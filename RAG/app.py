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
    "doc_outlines": None,     # str – structural outline of uploaded docs
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
                "num_ctx": 8192,
            },
        }
        resp = http_requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=300,
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


# ── Broad-question helpers ────────────────────────────────────────────────

_BROAD_KEYWORDS = [
    "tóm tắt", "tom tat", "nội dung chính", "noi dung chinh",
    "bao nhiêu", "bao nhieu", "tổng quan", "tong quan",
    "cấu trúc", "cau truc", "liệt kê", "liet ke",
    "có những", "co nhung", "gồm những", "gom nhung",
    "danh sách", "danh sach", "tổng số", "tong so",
    "mấy điều", "may dieu", "mấy khoản", "may khoan",
    "toàn bộ", "toan bo", "khái quát", "khai quat",
    "quy định gì", "quy dinh gi", "nói về", "noi ve",
    "đề cập", "de cap", "phạm vi", "pham vi",
]


_COMPARE_KEYWORDS = [
    "so sánh", "so sanh", "khác biệt", "khac biet", 
    "thay đổi", "thay doi", "điểm mới", "diem moi",
    "giống và khác", "giong va khac"
]

def _is_broad_question(query: str) -> bool:
    """Detect questions about the whole document (summary, structure, counts)."""
    return any(kw in query.lower() for kw in _BROAD_KEYWORDS)


def _extract_doc_outline(chunks: list, doc_name: str) -> str:
    """Extract a structural outline from document chunks."""
    headings = []
    dieu_count = 0
    chuong_count = 0
    muc_count = 0
    for c in chunks:
        if c.heading:
            headings.append(c.heading)
            h = c.heading.strip().lower()
            if h.startswith("điều") or h.startswith("dieu"):
                dieu_count += 1
            elif h.startswith("chương") or h.startswith("chuong"):
                chuong_count += 1
            elif h.startswith("mục") or h.startswith("muc"):
                muc_count += 1
    parts = [f"📄 Tài liệu: {doc_name}"]
    parts.append(f"  - Số chương: {chuong_count}")
    parts.append(f"  - Số mục: {muc_count}")
    parts.append(f"  - Số điều: {dieu_count}")
    parts.append(f"  - Tổng số đoạn nội dung: {len(chunks)}")
    if headings:
        parts.append("  - Danh sách cấu trúc:")
        for h in headings[:80]:
            parts.append(f"    • {h}")
        if len(headings) > 80:
            parts.append(f"    ... và {len(headings) - 80} mục khác")
    return "\n".join(parts)


def _build_outline_stats() -> dict | None:
    """Return structured outline stats for the frontend summary cards."""
    chunks = _session.get("temp_chunks")
    if not chunks:
        return None

    docs = {}
    for c in chunks:
        doc_id = c.doc_id
        if doc_id not in docs:
            docs[doc_id] = {
                "name": _session.get("doc1_name") if doc_id == Path(_session.get("doc1_path", "")).stem else _session.get("doc2_name"),
                "dieu": 0, "chuong": 0, "muc": 0, "chunks": 0, "headings": [],
            }
        docs[doc_id]["chunks"] += 1
        if c.heading:
            docs[doc_id]["headings"].append(c.heading)
            h = c.heading.strip().lower()
            if h.startswith("điều") or h.startswith("dieu"):
                docs[doc_id]["dieu"] += 1
            elif h.startswith("chương") or h.startswith("chuong"):
                docs[doc_id]["chuong"] += 1
            elif h.startswith("mục") or h.startswith("muc"):
                docs[doc_id]["muc"] += 1

    return {
        "documents": [
            {
                "name": info["name"] or doc_id,
                "chuong": info["chuong"],
                "muc": info["muc"],
                "dieu": info["dieu"],
                "chunks": info["chunks"],
                "headings": info["headings"][:30],
            }
            for doc_id, info in docs.items()
        ]
    }


# ═══════════════════════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("upload.html")


@app.route("/upload")
def upload_page():
    return render_template("upload.html")


@app.route("/comparison")
def comparison_page():
    return render_template("comparison.html")


@app.route("/chatbot")
def chatbot_page():
    return render_template("chatbot.html")


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
        outline_parts: List[str] = []
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
            # Extract outline for broad chatbot questions
            doc_name = _session.get(f"{label}_name", Path(path).name)
            outline_parts.append(_extract_doc_outline(chunks, doc_name))

        if all_chunks:
            texts = [c.text for c in all_chunks]
            index = _build_temp_index(texts, model_name)
            _session["temp_index"] = index
            _session["temp_chunks"] = all_chunks
        _session["doc_outlines"] = "\n\n".join(outline_parts) if outline_parts else None

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

        # Determine which index/chunks to use — only uploaded documents
        index = _session.get("temp_index")
        chunks = _session.get("temp_chunks")
        model_name = _session.get("model_name")

        if index is None or not chunks:
            return jsonify({
                "error": "Chưa có dữ liệu. Vui lòng upload tài liệu trước."
            }), 400

        if not model_name:
            model_name = resolve_model_name(OUTPUT_INDEX_DIR, None)

        # Detect broad/summary questions about the whole document
        is_broad = _is_broad_question(query)
        is_compare = any(kw in query.lower() for kw in _COMPARE_KEYWORDS)
        retrieval_top_k = 10 if is_broad else 5

        # Retrieve relevant chunks
        hits = retrieve_chunks(
            query=query,
            index=index,
            chunks=chunks if isinstance(chunks[0], ChunkRecord) else [],
            model_name=model_name,
            top_k=retrieval_top_k,
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

        # Tuần 11: Evidence gate — kiểm tra chất lượng retrieval trước khi gọi LLM
        evidence_weak = False
        if hits:
            top_score = hits[0].score
            if top_score < 0.45:  # Ngưỡng score thấp → evidence yếu
                evidence_weak = True

        # Try LLM response via Ollama
        llm_response = None
        llm_model_used = None
        
        # Build comparison context if requested
        compare_context = ""
        if is_compare and _session.get("doc1_text") and _session.get("doc2_text"):
            if not _session.get("compare_results"):
                diffs = compare_documents(_session.get("doc1_text"), _session.get("doc2_text"))
                stats = summary_stats(diffs)
                _session["compare_results"] = {"stats": stats, "diffs": [d.to_dict() for d in diffs]}
            
            stats = _session["compare_results"]["stats"]
            diff_dicts = _session["compare_results"]["diffs"]
            
            compare_context = f"THỐNG KÊ THAY ĐỔI GIỮA 2 TÀI LIỆU:\n- Thêm mới: {stats['added']}\n- Xóa bỏ: {stats['removed']}\n- Chỉnh sửa: {stats['modified']}\n\nCHI TIẾT ĐIỂM KHÁC BIỆT:\n"
            changed_diffs = [d for d in diff_dicts if d['diff_type'] != 'unchanged']
            for d in changed_diffs[:15]:
                heading = d['heading'] or "Phần chung"
                if d['diff_type'] == 'added':
                    compare_context += f"- Thêm mới tại [{heading}]: {d['new_text']}\n"
                elif d['diff_type'] == 'removed':
                    compare_context += f"- Xóa bỏ tại [{heading}]: {d['old_text']}\n"
                elif d['diff_type'] == 'modified':
                    compare_context += f"- Thay đổi tại [{heading}]:\n  + Cũ: {d['old_text']}\n  + Mới: {d['new_text']}\n"
            if len(changed_diffs) > 15:
                compare_context += f"\n... và {len(changed_diffs) - 15} thay đổi khác."
            
            evidence_weak = False  # Strong evidence from exact diffs

        if (hits or compare_context) and _check_ollama():
            context_hits = hits[:5] if is_broad else hits[:3]
            context = _format_retrieval_context(context_hits)

            # For broad questions, prepend document outlines so the LLM
            # has a bird's-eye view of the uploaded documents.
            doc_outlines = _session.get("doc_outlines")
            if is_broad and doc_outlines:
                context = (
                    f"TỔNG QUAN TÀI LIỆU:\n{doc_outlines}\n\n"
                    f"---\n\nCHI TIẾT LIÊN QUAN:\n{context}"
                )
                
            # For compare questions, prepend compare context
            if compare_context:
                context = (
                    f"{compare_context}\n\n"
                    f"---\n\nNGỮ CẢNH TÌM KIẾM BỔ SUNG:\n{context}"
                )

            # Tuần 11: Cải thiện system prompt — chain-of-thought + anti-hallucination
            system_prompt = (
                "Bạn là trợ lý pháp lý thông minh. Tuân thủ NGHIÊM NGẶT các quy tắc sau:\n\n"
                "1. CHỈ trả lời dựa trên ngữ cảnh được cung cấp. KHÔNG ĐƯỢC bịa thêm thông tin.\n"
                "2. Nếu ngữ cảnh KHÔNG chứa thông tin để trả lời, bạn PHẢI nói: "
                "'Tôi không tìm thấy thông tin này trong tài liệu được cung cấp.'\n"
                "3. Trước khi trả lời, hãy liệt kê bằng chứng tìm được theo format:\n"
                "   📌 Bằng chứng: [Điều/Khoản X, Tên_văn_bản]\n"
                "4. Sau đó mới đưa ra câu trả lời tổng hợp.\n"
                "5. Mọi khẳng định phải kèm trích dẫn nguồn cụ thể: [Điều X, Tên_văn_bản].\n"
                "6. Trả lời bằng tiếng Việt, ngắn gọn và chính xác.\n"
                "7. Khi câu hỏi yêu cầu tóm tắt, liệt kê, hoặc đếm số điều/khoản, "
                "hãy sử dụng phần TỔNG QUAN TÀI LIỆU nếu có."
            )
            evidence_note = ""
            if evidence_weak:
                evidence_note = (
                    "\n⚠️ LƯU Ý: Độ liên quan của ngữ cảnh thấp. "
                    "Hãy đặc biệt cẩn thận và chỉ trả lời nếu thực sự tìm thấy thông tin.\n"
                )
            user_prompt = (
                f"Ngữ cảnh:{evidence_note}\n{context}\n\n"
                f"Câu hỏi: {query}\n\n"
                "Hãy thực hiện:\n"
                "1. Liệt kê bằng chứng liên quan từ ngữ cảnh.\n"
                "2. Trả lời câu hỏi dựa trên bằng chứng đó.\n"
                "3. Trích dẫn nguồn [Điều X, Tên_văn_bản] cho mỗi khẳng định."
            )
            llm_response = _call_ollama(user_prompt, system_prompt)
            llm_model_used = _get_available_ollama_model()

        # Build response
        response_type = "summary" if is_broad else "retrieval"
        doc_outlines_data = _session.get("doc_outlines")

        if not hits and not compare_context:
            answer = "Không tìm thấy đoạn nào liên quan trong tài liệu."
            evidence_status = "INSUFFICIENT_EVIDENCE"
        else:
            evidence_status = "WEAK_EVIDENCE" if evidence_weak else "SUPPORTED"
            if llm_response:
                if evidence_weak:
                    answer = (
                        "⚠️ *Lưu ý: Độ liên quan của kết quả tìm kiếm thấp. "
                        "Câu trả lời có thể không chính xác.*\n\n" + llm_response
                    )
                else:
                    answer = llm_response
            elif is_compare and compare_context:
                answer = (
                    "⚠️ *Lưu ý: Không thể kết nối với mô hình AI (LLM) để tạo tóm tắt. Đây là kết quả so sánh trực tiếp:*\n\n" +
                    compare_context
                )
            elif is_broad and doc_outlines_data:
                # Broad question without LLM → structured summary from outlines
                answer = doc_outlines_data
            else:
                # Specific question without LLM → retrieval results
                parts = ["**Kết quả tìm kiếm liên quan:**\n"]
                for c in citations[:3]:
                    parts.append(
                        f"📌 **{c['heading']}** (score: {c['score']})\n"
                        f"*Nguồn: {Path(c['source_path']).name}*\n\n"
                        f"{c['text'][:500]}{'...' if len(c['text']) > 500 else ''}\n"
                    )
                answer = "\n---\n".join(parts)

        # Build outline_stats for frontend summary cards
        outline_stats = None
        if is_broad:
            outline_stats = _build_outline_stats()

        return jsonify({
            "query": query,
            "answer": answer,
            "response_type": response_type,
            "evidence_status": evidence_status,
            "llm_used": llm_response is not None,
            "llm_model": llm_model_used,
            "citations": citations,
            "outline_stats": outline_stats,
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
    print("  LegalDiff - Legal Document Comparison (RAG + Local LLM)")
    print("  URL: http://localhost:5000")
    print("=" * 60)

    if _check_ollama():
        model = _get_available_ollama_model()
        print(f"  [OK] Ollama running - Model: {model}")
    else:
        print("  [WARN] Ollama not running - Chatbot will use retrieval only")
        print(f"     To enable LLM: ollama serve & ollama pull {OLLAMA_MODEL}")
    print("=" * 60)

    app.run(host="0.0.0.0", port=5000, debug=True)
