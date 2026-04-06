#!/usr/bin/env python
"""
Flask web server — UI bản 1 cho hệ thống so sánh văn bản pháp lý RAG.
Chạy: python app.py
Truy cập: http://localhost:5000
"""

import json
import os
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
import requests as http_requests
from flask import Flask, jsonify, render_template, request

from compare_engine import compare_documents, summary_stats
from rag_pipeline import (
    ChunkRecord,
    build_embeddings,
    build_faiss_index,
    chunk_document,
    DocumentRecord,
    get_embedding_model,
    load_metadata,
    normalize_text,
    read_docx,
    read_txt,
    resolve_model_name,
    retrieve_chunks,
    save_manifest,
    save_metadata,
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_INDEX_DIR = BASE_DIR / "output_index"

# ── Session state (in‑memory, single‑user local prototype) ──────────────
_session: Dict[str, Any] = {
    "doc1_path": None,
    "doc2_path": None,
    "doc1_text": None,
    "doc2_text": None,
    "doc1_name": None,
    "doc2_name": None,
    "compare_results": None,
    "temp_index": None,       # faiss.Index
    "temp_chunks": None,      # List[ChunkRecord]
    "model_name": None,
}

# Ollama settings
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _read_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".docx":
        return read_docx(path)
    elif ext in (".txt", ".text"):
        return read_txt(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Chỉ hỗ trợ .docx và .txt")


def _build_temp_index(texts: List[str], model_name: str) -> tuple:
    """Build a temporary FAISS index from a list of texts."""
    embeddings = build_embeddings(texts, model_name, batch_size=16)
    index = build_faiss_index(embeddings)
    return index


def _check_ollama() -> bool:
    """Check if Ollama is running and the configured model is available."""
    try:
        resp = http_requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            available = [m.get("name", "") for m in models]
            # Check if our model (or a variant) is available
            for name in available:
                if OLLAMA_MODEL.split(":")[0] in name:
                    return True
            # If we have any models, use the first one
            if available:
                return True
        return False
    except Exception:
        return False


def _get_available_ollama_model() -> Optional[str]:
    """Get the first available Ollama model name."""
    try:
        resp = http_requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            available = [m.get("name", "") for m in models]
            # Prefer configured model
            for name in available:
                if OLLAMA_MODEL.split(":")[0] in name:
                    return name
            if available:
                return available[0]
    except Exception:
        pass
    return None


def _call_ollama(prompt: str, system_prompt: str = "") -> Optional[str]:
    """Call Ollama API to generate a response."""
    model = _get_available_ollama_model()
    if not model:
        return None
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 1024,
            },
        }
        resp = http_requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=120,
        )
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except Exception:
        pass
    return None


def _format_retrieval_context(hits: list) -> str:
    """Format retrieval hits as context for LLM."""
    parts = []
    for hit in hits:
        heading = hit.chunk.heading or "(không có heading)"
        parts.append(
            f"[Nguồn: {hit.chunk.source_path} | {heading}]\n{hit.chunk.text}"
        )
    return "\n\n---\n\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def api_status():
    """Return current session status."""
    ollama_ok = _check_ollama()
    ollama_model = _get_available_ollama_model() if ollama_ok else None
    return jsonify({
        "doc1_loaded": _session["doc1_name"] is not None,
        "doc2_loaded": _session["doc2_name"] is not None,
        "doc1_name": _session["doc1_name"],
        "doc2_name": _session["doc2_name"],
        "has_compare": _session["compare_results"] is not None,
        "has_index": _session["temp_index"] is not None,
        "ollama_available": ollama_ok,
        "ollama_model": ollama_model,
    })


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Upload one or two documents."""
    try:
        file1 = request.files.get("doc1")
        file2 = request.files.get("doc2")

        if not file1 and not file2:
            return jsonify({"error": "Vui lòng upload ít nhất 1 file"}), 400

        model_name = resolve_model_name(OUTPUT_INDEX_DIR, None)
        _session["model_name"] = model_name

        if file1 and file1.filename:
            path1 = UPLOAD_DIR / file1.filename
            file1.save(str(path1))
            _session["doc1_path"] = path1
            _session["doc1_text"] = normalize_text(_read_file(path1))
            _session["doc1_name"] = file1.filename

        if file2 and file2.filename:
            path2 = UPLOAD_DIR / file2.filename
            file2.save(str(path2))
            _session["doc2_path"] = path2
            _session["doc2_text"] = normalize_text(_read_file(path2))
            _session["doc2_name"] = file2.filename

        # Clear old comparison results
        _session["compare_results"] = None

        # Build temporary index from both docs for chatbot retrieval
        all_chunks: List[ChunkRecord] = []
        for label, text, path in [
            ("doc1", _session.get("doc1_text"), _session.get("doc1_path")),
            ("doc2", _session.get("doc2_text"), _session.get("doc2_path")),
        ]:
            if not text or not path:
                continue
            doc = DocumentRecord(
                doc_id=Path(path).stem,
                source_path=str(path),
                text=text,
            )
            chunks = chunk_document(doc, max_words=600, overlap_words=80, min_words=40)
            all_chunks.extend(chunks)

        if all_chunks:
            texts = [c.text for c in all_chunks]
            index = _build_temp_index(texts, model_name)
            _session["temp_index"] = index
            _session["temp_chunks"] = all_chunks

        return jsonify({
            "success": True,
            "doc1_name": _session["doc1_name"],
            "doc2_name": _session["doc2_name"],
            "chunk_count": len(all_chunks),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/documents", methods=["GET"])
def api_documents():
    """Get uploaded document contents for side-by-side view."""
    return jsonify({
        "doc1": {
            "name": _session.get("doc1_name"),
            "text": _session.get("doc1_text"),
        },
        "doc2": {
            "name": _session.get("doc2_name"),
            "text": _session.get("doc2_text"),
        },
    })


@app.route("/api/compare", methods=["POST"])
def api_compare():
    """Compare two uploaded documents."""
    try:
        doc1_text = _session.get("doc1_text")
        doc2_text = _session.get("doc2_text")

        if not doc1_text or not doc2_text:
            return jsonify({"error": "Cần upload đủ 2 tài liệu trước khi so sánh"}), 400

        diffs = compare_documents(doc1_text, doc2_text)
        stats = summary_stats(diffs)

        result = {
            "stats": stats,
            "diffs": [d.to_dict() for d in diffs],
        }
        _session["compare_results"] = result
        return jsonify(result)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """RAG chatbot: query → retrieval → (optional) LLM → response with citations."""
    try:
        data = request.get_json(force=True)
        query = data.get("query", "").strip()
        if not query:
            return jsonify({"error": "Câu hỏi không được để trống"}), 400

        # Determine which index/chunks to use
        index = _session.get("temp_index")
        chunks = _session.get("temp_chunks")
        model_name = _session.get("model_name")

        # Fallback to global index if no temp index
        if index is None:
            index_path = OUTPUT_INDEX_DIR / "index.faiss"
            if index_path.exists():
                index = faiss.read_index(str(index_path))
                chunks = load_metadata(OUTPUT_INDEX_DIR)
                # Convert dict metadata to ChunkRecord
                chunks = [
                    ChunkRecord(
                        chunk_id=c.get("chunk_id", ""),
                        doc_id=c.get("doc_id", ""),
                        source_path=c.get("source_path", ""),
                        heading=c.get("heading"),
                        text=c.get("text", ""),
                        order=int(c.get("order", 0)),
                    )
                    if isinstance(c, dict) else c
                    for c in chunks
                ]

        if index is None or not chunks:
            return jsonify({
                "error": "Chưa có dữ liệu. Vui lòng upload tài liệu trước."
            }), 400

        if not model_name:
            model_name = resolve_model_name(OUTPUT_INDEX_DIR, None)

        # Retrieve relevant chunks
        hits = retrieve_chunks(
            query=query,
            index=index,
            chunks=chunks if isinstance(chunks[0], ChunkRecord) else [],
            model_name=model_name,
            top_k=5,
            clause_filter=False,
        )

        # Format citations
        citations = []
        for hit in hits:
            citations.append({
                "rank": hit.rank,
                "score": round(hit.score, 4),
                "chunk_id": hit.chunk.chunk_id,
                "doc_id": hit.chunk.doc_id,
                "heading": hit.chunk.heading or "(không có heading)",
                "source_path": hit.chunk.source_path,
                "text": hit.chunk.text,
            })

        # Try LLM response via Ollama
        llm_response = None
        llm_model_used = None
        if hits and _check_ollama():
            context = _format_retrieval_context(hits[:3])
            system_prompt = (
                "Bạn là trợ lý pháp lý thông minh. Trả lời câu hỏi dựa HOÀN TOÀN vào "
                "ngữ cảnh được cung cấp. Nếu ngữ cảnh không đủ thông tin, hãy nói rõ. "
                "Luôn trích dẫn nguồn (heading + tên văn bản). "
                "Trả lời bằng tiếng Việt, ngắn gọn và chính xác."
            )
            user_prompt = (
                f"Ngữ cảnh:\n{context}\n\n"
                f"Câu hỏi: {query}\n\n"
                "Hãy trả lời dựa trên ngữ cảnh trên. Trích dẫn nguồn cụ thể."
            )
            llm_response = _call_ollama(user_prompt, system_prompt)
            llm_model_used = _get_available_ollama_model()

        # Build response
        if not hits:
            answer = "Không tìm thấy đoạn nào liên quan trong tài liệu."
            evidence_status = "INSUFFICIENT_EVIDENCE"
        else:
            evidence_status = "SUPPORTED"
            if llm_response:
                answer = llm_response
            else:
                # Fallback: format retrieval results as answer
                parts = ["**Kết quả tìm kiếm liên quan:**\n"]
                for c in citations[:3]:
                    parts.append(
                        f"📌 **{c['heading']}** (score: {c['score']})\n"
                        f"*Nguồn: {Path(c['source_path']).name}*\n\n"
                        f"{c['text'][:500]}{'...' if len(c['text']) > 500 else ''}\n"
                    )
                answer = "\n---\n".join(parts)

        return jsonify({
            "query": query,
            "answer": answer,
            "evidence_status": evidence_status,
            "llm_used": llm_response is not None,
            "llm_model": llm_model_used,
            "citations": citations,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Reset session state."""
    for k in _session:
        _session[k] = None
    return jsonify({"success": True})


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Trợ lý so sánh văn bản pháp lý — RAG + Local LLM")
    print("  Địa chỉ: http://localhost:5000")
    print("=" * 60)

    if _check_ollama():
        model = _get_available_ollama_model()
        print(f"  ✅ Ollama đang chạy — Model: {model}")
    else:
        print("  ⚠️  Ollama chưa chạy — Chatbot sẽ dùng retrieval thuần")
        print(f"     Để bật LLM: ollama serve & ollama pull {OLLAMA_MODEL}")
    print("=" * 60)

    app.run(host="0.0.0.0", port=5000, debug=True)
