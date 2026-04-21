#!/usr/bin/env python
import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from docx import Document
from sentence_transformers import SentenceTransformer
import faiss


HEADING_RE = re.compile(
    r"^(Điều|Dieu|Khoản|Khoan|Mục|Muc|Chương|Chuong|Phần|Phan|Phụ lục|Phu luc)\s+([0-9IVXLC]+(?:[.\-][0-9]+)*)",
    re.IGNORECASE,
)
KHOAN_DIEU_RE = re.compile(
    r"(?:Khoản|Khoan)\s+(\d+)\s+(?:,\s*)?(?:Điều|Dieu)\s+([0-9IVXLC]+)",
    re.IGNORECASE,
)
DIEU_RE = re.compile(r"(?:Điều|Dieu)\s+([0-9IVXLC]+)", re.IGNORECASE)

# Tuần 11: Broken heading merge patterns
_HEADING_PREFIX_ONLY_RE = re.compile(
    r"^(Điều|Dieu|Khoản|Khoan|Mục|Muc|Chương|Chuong|Phần|Phan)\s*$",
    re.IGNORECASE,
)
_HEADING_NUMBER_START_RE = re.compile(r"^\s*([0-9IVXLC]+)")


MODEL_CACHE: Dict[str, SentenceTransformer] = {}


@dataclass
class DocumentRecord:
    doc_id: str
    source_path: str
    text: str


@dataclass
class ChunkRecord:
    chunk_id: str
    doc_id: str
    source_path: str
    heading: Optional[str]
    text: str
    order: int


@dataclass
class RetrievalHit:
    rank: int
    score: float
    chunk: ChunkRecord


def read_docx(file_path: Path) -> str:
    doc = Document(str(file_path))
    parts = [p.text for p in doc.paragraphs if p.text]
    return "\n".join(parts)


def read_doc(file_path: Path) -> str:
    try:
        import textract
    except ImportError as exc:
        raise RuntimeError(
            "Missing optional dependency for .doc files. Install textract to read .doc."
        ) from exc
    content = textract.process(str(file_path))
    return content.decode("utf-8", errors="ignore")


def read_txt(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="ignore")


def _merge_broken_headings(text: str) -> str:
    """Ghép heading bị tách qua nhiều dòng (tuần 11).
    Ví dụ: 'Điều\n11. Nội dung' → 'Điều 11. Nội dung'
    """
    lines = text.split("\n")
    merged: list = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if _HEADING_PREFIX_ONLY_RE.match(stripped):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and _HEADING_NUMBER_START_RE.match(lines[j].strip()):
                merged.append(stripped + " " + lines[j].strip())
                i = j + 1
                continue
        merged.append(lines[i])
        i += 1
    return "\n".join(merged)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = _merge_broken_headings(text)  # Tuần 11: merge broken headings
    return text.strip()


def normalize_for_match(text: str) -> str:
    no_accents = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    no_accents = no_accents.lower()
    no_accents = re.sub(r"\s+", " ", no_accents)
    return no_accents.strip()


def extract_clause_refs(text: str) -> Set[str]:
    refs: Set[str] = set()
    normalized = normalize_for_match(text)

    for match in KHOAN_DIEU_RE.finditer(normalized):
        khoan_no = match.group(1)
        dieu_no = match.group(2)
        refs.add(f"khoan {khoan_no} dieu {dieu_no}")

    for match in DIEU_RE.finditer(normalized):
        dieu_no = match.group(1)
        refs.add(f"dieu {dieu_no}")

    return refs


def iter_documents(input_dir: Path) -> Iterable[DocumentRecord]:
    for file_path in input_dir.rglob("*"):
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if ext not in {".doc", ".docx", ".txt"}:
            continue

        if ext == ".docx":
            raw = read_docx(file_path)
        elif ext == ".doc":
            raw = read_doc(file_path)
        else:
            raw = read_txt(file_path)

        norm = normalize_text(raw)
        doc_id = file_path.stem
        yield DocumentRecord(doc_id=doc_id, source_path=str(file_path), text=norm)


def split_by_headings(text: str) -> List[ChunkRecord]:
    lines = text.split("\n")
    sections: List[ChunkRecord] = []
    current_heading: Optional[str] = None
    current_lines: List[str] = []
    order = 0

    def flush():
        nonlocal order
        if not current_lines:
            return
        chunk_text = "\n".join(current_lines).strip()
        if chunk_text:
            sections.append(
                ChunkRecord(
                    chunk_id="",
                    doc_id="",
                    source_path="",
                    heading=current_heading,
                    text=chunk_text,
                    order=order,
                )
            )
            order += 1

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            current_lines.append("")
            continue
        if HEADING_RE.match(line_stripped):
            flush()
            current_heading = line_stripped
            current_lines = [line_stripped]
        else:
            current_lines.append(line_stripped)

    flush()
    return sections


def split_long_chunk(text: str, max_words: int, overlap_words: int) -> List[str]:
    words = text.split()
    if len(words) <= max_words:
        return [text]
    chunks: List[str] = []
    step = max_words - overlap_words
    if step <= 0:
        step = max_words
    i = 0
    while i < len(words):
        chunk_words = words[i : i + max_words]
        chunks.append(" ".join(chunk_words))
        i += step
    return chunks


def chunk_document(
    doc: DocumentRecord,
    max_words: int,
    overlap_words: int,
    min_words: int,
) -> List[ChunkRecord]:
    sections = split_by_headings(doc.text)
    if not sections:
        sections = [
            ChunkRecord(
                chunk_id="",
                doc_id=doc.doc_id,
                source_path=doc.source_path,
                heading=None,
                text=doc.text,
                order=0,
            )
        ]

    chunks: List[ChunkRecord] = []
    order = 0
    for section in sections:
        base_text = section.text
        heading = section.heading
        sub_texts = split_long_chunk(base_text, max_words, overlap_words)
        for sub_text in sub_texts:
            if len(sub_text.split()) < min_words:
                continue
            chunk_id = f"{doc.doc_id}::{order}"
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    doc_id=doc.doc_id,
                    source_path=doc.source_path,
                    heading=heading,
                    text=sub_text,
                    order=order,
                )
            )
            order += 1
    return chunks


def build_embeddings(
    texts: List[str],
    model_name: str,
    batch_size: int,
) -> List[List[float]]:
    model = get_embedding_model(model_name)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    return embeddings


def build_faiss_index(embeddings) -> faiss.Index:
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index


def save_metadata(chunks: List[ChunkRecord], output_dir: Path) -> None:
    metadata_path = output_dir / "metadata.jsonl"
    with metadata_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            payload = {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "source_path": chunk.source_path,
                "heading": chunk.heading,
                "order": chunk.order,
                "text": chunk.text,
            }
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def save_manifest(output_dir: Path, config: dict) -> None:
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": config,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def get_embedding_model(model_name: str) -> SentenceTransformer:
    model = MODEL_CACHE.get(model_name)
    if model is None:
        model = SentenceTransformer(model_name)
        MODEL_CACHE[model_name] = model
    return model


def load_metadata(index_dir: Path) -> List[ChunkRecord]:
    metadata_path = index_dir / "metadata.jsonl"
    chunks: List[ChunkRecord] = []
    with metadata_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            chunks.append(
                ChunkRecord(
                    chunk_id=payload.get("chunk_id", ""),
                    doc_id=payload.get("doc_id", ""),
                    source_path=payload.get("source_path", ""),
                    heading=payload.get("heading"),
                    text=payload.get("text", ""),
                    order=int(payload.get("order", 0)),
                )
            )
    return chunks


def resolve_model_name(index_dir: Path, model_name: Optional[str]) -> str:
    if model_name:
        return model_name

    manifest_path = index_dir / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            config = manifest.get("config", {})
            configured = config.get("model_name")
            if configured:
                return configured
        except (json.JSONDecodeError, OSError):
            pass
    return "BAAI/bge-m3"


def chunk_matches_clause(chunk: ChunkRecord, clause_refs: Set[str]) -> bool:
    if not clause_refs:
        return True

    heading_text = normalize_for_match(chunk.heading or "")
    body_text = normalize_for_match(chunk.text)

    for ref in clause_refs:
        if ref in heading_text or ref in body_text:
            return True
    return False


def retrieval_boost(chunk: ChunkRecord, clause_refs: Set[str]) -> float:
    if not clause_refs:
        # Tuần 11: penalty nhẹ cho chunk không có heading khi query có clause refs
        return 0.0

    heading_text = normalize_for_match(chunk.heading or "")
    body_text = normalize_for_match(chunk.text)

    boost = 0.0
    for ref in clause_refs:
        if ref in heading_text:
            boost += 0.30   # Tuần 11: tăng từ 0.25 → 0.30
        elif ref in body_text:
            boost += 0.10

    # Tuần 11: penalty nhẹ cho chunk không có heading
    if not chunk.heading and clause_refs:
        boost -= 0.05

    return boost


def retrieve_chunks(
    query: str,
    index: faiss.Index,
    chunks: List[ChunkRecord],
    model_name: str,
    top_k: int,
    clause_filter: bool,
) -> List[RetrievalHit]:
    clause_refs = extract_clause_refs(query)

    model = get_embedding_model(model_name)
    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    candidate_k = min(max(top_k * 4, top_k), len(chunks))
    scores, indices = index.search(query_embedding, candidate_k)

    candidates: List[RetrievalHit] = []
    for raw_score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        chunk = chunks[idx]
        if clause_filter and not chunk_matches_clause(chunk, clause_refs):
            continue
        final_score = float(raw_score) + retrieval_boost(chunk, clause_refs)
        candidates.append(RetrievalHit(rank=0, score=final_score, chunk=chunk))

    candidates.sort(key=lambda hit: hit.score, reverse=True)

    selected = candidates[:top_k]
    for i, hit in enumerate(selected, start=1):
        hit.rank = i
    return selected


def summarize_text(text: str, max_chars: int) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."


def build_database_report(index_dir: Path, chunks: List[ChunkRecord], index: faiss.Index) -> dict:
    docs = {c.doc_id for c in chunks}
    with_heading = [c for c in chunks if c.heading]
    word_counts = [len(c.text.split()) for c in chunks]
    heading_counts: Dict[str, int] = {}
    for chunk in with_heading:
        key = chunk.heading or ""
        heading_counts[key] = heading_counts.get(key, 0) + 1

    top_headings = sorted(heading_counts.items(), key=lambda item: item[1], reverse=True)[:10]
    return {
        "index_dir": str(index_dir),
        "vector_count": int(index.ntotal),
        "vector_dim": int(index.d),
        "chunk_count": len(chunks),
        "document_count": len(docs),
        "chunks_with_heading": len(with_heading),
        "heading_coverage": round(len(with_heading) / len(chunks), 4) if chunks else 0,
        "avg_words_per_chunk": round(sum(word_counts) / len(word_counts), 2) if word_counts else 0,
        "min_words_per_chunk": min(word_counts) if word_counts else 0,
        "max_words_per_chunk": max(word_counts) if word_counts else 0,
        "top_headings": [{"heading": heading, "chunks": count} for heading, count in top_headings],
    }


def build_pipeline(args: argparse.Namespace) -> None:
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_chunks: List[ChunkRecord] = []
    for doc in iter_documents(input_dir):
        chunks = chunk_document(
            doc,
            max_words=args.max_words,
            overlap_words=args.overlap_words,
            min_words=args.min_words,
        )
        all_chunks.extend(chunks)

    if not all_chunks:
        raise RuntimeError("No chunks generated from input documents.")

    texts = [c.text for c in all_chunks]
    embeddings = build_embeddings(texts, args.model_name, args.batch_size)
    index = build_faiss_index(embeddings)

    faiss.write_index(index, str(output_dir / "index.faiss"))
    save_metadata(all_chunks, output_dir)
    save_manifest(
        output_dir,
        {
            "input_dir": str(input_dir),
            "model_name": args.model_name,
            "max_words": args.max_words,
            "overlap_words": args.overlap_words,
            "min_words": args.min_words,
            "batch_size": args.batch_size,
        },
    )


def run_query_command(args: argparse.Namespace) -> None:
    index_dir = Path(args.index_dir)
    index = faiss.read_index(str(index_dir / "index.faiss"))
    chunks = load_metadata(index_dir)

    if index.ntotal != len(chunks):
        raise RuntimeError(
            f"Index vector count ({index.ntotal}) does not match metadata chunks ({len(chunks)})."
        )

    model_name = resolve_model_name(index_dir, args.model_name)
    hits = retrieve_chunks(
        query=args.query,
        index=index,
        chunks=chunks,
        model_name=model_name,
        top_k=args.top_k,
        clause_filter=args.clause_filter,
    )

    if args.json:
        payload = {
            "query": args.query,
            "model_name": model_name,
            "top_k": args.top_k,
            "results": [
                {
                    "rank": hit.rank,
                    "score": round(hit.score, 6),
                    "chunk_id": hit.chunk.chunk_id,
                    "doc_id": hit.chunk.doc_id,
                    "heading": hit.chunk.heading,
                    "source_path": hit.chunk.source_path,
                    "order": hit.chunk.order,
                    "text": hit.chunk.text,
                }
                for hit in hits
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print(f"Query: {args.query}")
    print(f"Model: {model_name}")
    print(f"Results: {len(hits)}")
    print("-" * 80)
    for hit in hits:
        heading = hit.chunk.heading or "(không có heading)"
        print(f"#{hit.rank} | score={hit.score:.4f} | {hit.chunk.chunk_id}")
        print(f"  heading: {heading}")
        print(f"  source : {hit.chunk.source_path}")
        print(f"  text   : {summarize_text(hit.chunk.text, args.show_text_chars)}")
        print("-" * 80)


def run_report_command(args: argparse.Namespace) -> None:
    index_dir = Path(args.index_dir)
    index = faiss.read_index(str(index_dir / "index.faiss"))
    chunks = load_metadata(index_dir)
    model_name = resolve_model_name(index_dir, args.model_name)

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database": build_database_report(index_dir, chunks, index),
        "queries": [],
    }

    demo_queries = args.demo_query or []
    for q in demo_queries:
        hits = retrieve_chunks(
            query=q,
            index=index,
            chunks=chunks,
            model_name=model_name,
            top_k=args.top_k,
            clause_filter=args.clause_filter,
        )
        report["queries"].append(
            {
                "query": q,
                "results": [
                    {
                        "rank": hit.rank,
                        "score": round(hit.score, 6),
                        "chunk_id": hit.chunk.chunk_id,
                        "heading": hit.chunk.heading,
                        "source_path": hit.chunk.source_path,
                        "snippet": summarize_text(hit.chunk.text, args.show_text_chars),
                    }
                    for hit in hits
                ],
            }
        )

    report_json = json.dumps(report, ensure_ascii=False, indent=2)
    print(report_json)

    if args.output_file:
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_json, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RAG indexing, retrieval and reporting tool.")
    subparsers = parser.add_subparsers(dest="command")

    index_parser = subparsers.add_parser("index", help="Build FAISS index from DOC/DOCX/TXT")
    index_parser.add_argument("--input-dir", required=True, help="Folder with DOC/DOCX/TXT files")
    index_parser.add_argument(
        "--output-dir",
        required=True,
        help="Folder to store FAISS index and metadata",
    )
    index_parser.add_argument("--model-name", default="BAAI/bge-m3", help="Embedding model name")
    index_parser.add_argument("--batch-size", type=int, default=16)
    index_parser.add_argument("--max-words", type=int, default=600)
    index_parser.add_argument("--overlap-words", type=int, default=80)
    index_parser.add_argument("--min-words", type=int, default=40)

    query_parser = subparsers.add_parser("query", help="Retrieve relevant chunks from existing index")
    query_parser.add_argument("--index-dir", default="output_index", help="Folder containing index.faiss")
    query_parser.add_argument("--query", required=True, help="User query")
    query_parser.add_argument("--top-k", type=int, default=5, help="Number of chunks to return")
    query_parser.add_argument("--model-name", default=None, help="Embedding model (default from manifest)")
    query_parser.add_argument(
        "--clause-filter",
        action="store_true",
        help="Only keep chunks that explicitly contain Điều/Khoản references found in the query",
    )
    query_parser.add_argument("--json", action="store_true", help="Print results in JSON")
    query_parser.add_argument(
        "--show-text-chars",
        type=int,
        default=280,
        help="Snippet length for text output",
    )

    report_parser = subparsers.add_parser("report", help="Generate database and query demo report")
    report_parser.add_argument("--index-dir", default="output_index", help="Folder containing index.faiss")
    report_parser.add_argument("--top-k", type=int, default=3, help="Top-k results per demo query")
    report_parser.add_argument("--model-name", default=None, help="Embedding model (default from manifest)")
    report_parser.add_argument(
        "--demo-query",
        action="append",
        default=[],
        help="Demo query text; can be passed multiple times",
    )
    report_parser.add_argument(
        "--clause-filter",
        action="store_true",
        help="Only keep chunks that explicitly contain Điều/Khoản references found in each demo query",
    )
    report_parser.add_argument(
        "--show-text-chars",
        type=int,
        default=220,
        help="Snippet length in report query results",
    )
    report_parser.add_argument("--output-file", help="Optional path to save report JSON")

    # Backward compatibility: if the first arg is an option, treat it as legacy index mode.
    argv = sys.argv[1:]
    if argv and argv[0].startswith("-"):
        argv = ["index", *argv]
    elif not argv:
        parser.print_help()
        sys.exit(1)

    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    if args.command == "index":
        build_pipeline(args)
    elif args.command == "query":
        run_query_command(args)
    elif args.command == "report":
        run_report_command(args)
    else:
        raise RuntimeError("Unknown command. Use one of: index, query, report")
