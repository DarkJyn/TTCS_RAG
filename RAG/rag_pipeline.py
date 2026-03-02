#!/usr/bin/env python
import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from docx import Document
from sentence_transformers import SentenceTransformer
import faiss


HEADING_RE = re.compile(
    r"^(Điều|Dieu|Khoản|Khoan|Mục|Muc)\s+([0-9IVXLC]+(?:[.\-][0-9]+)*)",
    re.IGNORECASE,
)


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


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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
    model = SentenceTransformer(model_name)
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
        "created_at": datetime.utcnow().isoformat() + "Z",
        "config": config,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build vector embedding database from DOCX/PDF.")
    parser.add_argument("--input-dir", required=True, help="Folder with DOCX/PDF files")
    parser.add_argument("--output-dir", required=True, help="Folder to store FAISS index and metadata")
    parser.add_argument("--model-name", default="BAAI/bge-m3", help="Embedding model name")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-words", type=int, default=600)
    parser.add_argument("--overlap-words", type=int, default=80)
    parser.add_argument("--min-words", type=int, default=40)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_pipeline(args)
