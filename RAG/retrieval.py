#!/usr/bin/env python
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


def _configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load_manifest(index_dir: Path) -> Dict[str, Any]:
    manifest_path = index_dir / "manifest.json"
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def load_metadata(index_dir: Path) -> List[Dict[str, Any]]:
    metadata_path = index_dir / "metadata.jsonl"
    rows: List[Dict[str, Any]] = []
    with metadata_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def embed_query(query: str, model_name: str) -> np.ndarray:
    model = SentenceTransformer(model_name)
    vec = model.encode([query], normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vec, dtype="float32")


def search(
    index: faiss.Index,
    query_vec: np.ndarray,
    top_k: int,
) -> Tuple[np.ndarray, np.ndarray]:
    scores, ids = index.search(query_vec, top_k)
    return scores[0], ids[0]


def format_snippet(text: str, limit: int) -> str:
    t = " ".join(text.split())
    if len(t) <= limit:
        return t
    return t[: max(0, limit - 3)] + "..."


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Retrieve top-k chunks from a FAISS index.")
    p.add_argument("--index-dir", default="output_index", help="Folder with index.faiss + metadata.jsonl")
    p.add_argument("--query", default=None, help="Query text (semantic search). Optional if using heading/doc filters only.")
    p.add_argument("--top-k", type=int, default=5, help="Number of chunks to return")
    p.add_argument("--model-name", default=None, help="Override embedding model name")
    p.add_argument("--min-score", type=float, default=None, help="Filter results below this score")
    p.add_argument(
        "--heading-contains",
        default=None,
        help='Filter by heading substring (case-insensitive), e.g. "Điều 8" or "Khoản 2".',
    )
    p.add_argument(
        "--doc-contains",
        default=None,
        help='Filter by source/doc substring (case-insensitive), matched against doc_id and source_path.',
    )
    p.add_argument(
        "--oversample",
        type=int,
        default=None,
        help="When using query+filters, search this many candidates then filter down to top-k.",
    )
    p.add_argument("--snippet-chars", type=int, default=280, help="Snippet length for display")
    p.add_argument("--show-text", action="store_true", help="Print full chunk text")
    return p.parse_args()


def _matches_filters(row: Dict[str, Any], heading_contains: Optional[str], doc_contains: Optional[str]) -> bool:
    if heading_contains:
        h = (row.get("heading") or "")
        if heading_contains.casefold() not in str(h).casefold():
            return False
    if doc_contains:
        doc_id = str(row.get("doc_id") or "")
        src = str(row.get("source_path") or "")
        needle = doc_contains.casefold()
        if needle not in doc_id.casefold() and needle not in src.casefold():
            return False
    return True


def main() -> None:
    _configure_utf8_output()
    args = parse_args()
    index_dir = Path(args.index_dir)

    manifest = load_manifest(index_dir)
    manifest_model = (manifest.get("config") or {}).get("model_name")
    model_name = args.model_name or manifest_model or "BAAI/bge-m3"

    index_path = index_dir / "index.faiss"
    if not index_path.exists():
        raise SystemExit(f"Missing index file: {index_path}")

    metadata = load_metadata(index_dir)
    index = faiss.read_index(str(index_path))
    if metadata and len(metadata) != index.ntotal:
        raise SystemExit(
            f"Metadata/index size mismatch: metadata={len(metadata)} vs index.ntotal={index.ntotal}"
        )

    print(f"model_name: {model_name}")
    print(f"index_dir: {index_dir}")
    print(f"index.ntotal: {index.ntotal} | dim: {index.d}")
    if args.query is not None:
        print(f"query: {args.query}")
    if args.heading_contains:
        print(f"heading_contains: {args.heading_contains}")
    if args.doc_contains:
        print(f"doc_contains: {args.doc_contains}")
    print("")

    if args.query is None and not args.heading_contains and not args.doc_contains:
        raise SystemExit("Provide --query or at least one of --heading-contains / --doc-contains.")

    any_hit = False
    shown = 0

    if args.query is None:
        for idx, row in enumerate(metadata):
            if not _matches_filters(row, args.heading_contains, args.doc_contains):
                continue
            any_hit = True
            shown += 1
            chunk_id = row.get("chunk_id")
            source_path = row.get("source_path")
            heading = row.get("heading")
            text = row.get("text") or ""

            print(f"[{shown}] id={idx}  chunk_id={chunk_id}")
            if heading:
                print(f"    heading: {heading}")
            if source_path:
                print(f"    source: {source_path}")
            if args.show_text:
                print("    text:")
                for line in str(text).splitlines():
                    print(f"      {line}")
            else:
                print(f"    snippet: {format_snippet(str(text), args.snippet_chars)}")
            print("")

            if shown >= args.top_k:
                break
    else:
        oversample = args.oversample or max(args.top_k * 20, 50)
        qvec = embed_query(args.query, model_name=model_name)
        scores, ids = search(index, qvec, top_k=oversample)

        for score, idx in zip(scores.tolist(), ids.tolist()):
            if idx < 0:
                continue
            if args.min_score is not None and score < args.min_score:
                continue
            row: Optional[Dict[str, Any]] = metadata[idx] if metadata else None
            if row and not _matches_filters(row, args.heading_contains, args.doc_contains):
                continue

            any_hit = True
            shown += 1
            chunk_id = row.get("chunk_id") if row else str(idx)
            source_path = row.get("source_path") if row else None
            heading = row.get("heading") if row else None
            text = row.get("text") if row else ""

            print(f"[{shown}] score={score:.4f}  id={idx}  chunk_id={chunk_id}")
            if heading:
                print(f"    heading: {heading}")
            if source_path:
                print(f"    source: {source_path}")
            if args.show_text:
                print("    text:")
                for line in str(text).splitlines():
                    print(f"      {line}")
            else:
                print(f"    snippet: {format_snippet(str(text), args.snippet_chars)}")
            print("")

            if shown >= args.top_k:
                break

    if not any_hit:
        print("No results matched the given filters.")


if __name__ == "__main__":
    main()

