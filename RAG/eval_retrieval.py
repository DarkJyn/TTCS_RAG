#!/usr/bin/env python
import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

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
    p = index_dir / "manifest.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def load_metadata(index_dir: Path) -> List[Dict[str, Any]]:
    p = index_dir / "metadata.jsonl"
    rows: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON on line {i} of {path}: {exc}") from exc


def embed_queries(model: SentenceTransformer, queries: Sequence[str], batch_size: int) -> np.ndarray:
    vecs = model.encode(
        list(queries),
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    return np.asarray(vecs, dtype="float32")


def dcg_at_k(rels: Sequence[int], k: int) -> float:
    s = 0.0
    for i, rel in enumerate(rels[:k], start=1):
        if rel <= 0:
            continue
        s += rel / math.log2(i + 1)
    return s


def ndcg_at_k(rels: Sequence[int], k: int, num_relevant_total: int) -> float:
    if num_relevant_total <= 0:
        return 0.0
    dcg = dcg_at_k(rels, k)
    ideal_rels = [1] * min(k, num_relevant_total)
    idcg = dcg_at_k(ideal_rels, k)
    if idcg == 0:
        return 0.0
    return dcg / idcg


def parse_k_list(values: List[str]) -> List[int]:
    ks: List[int] = []
    for v in values:
        for part in v.split(","):
            part = part.strip()
            if not part:
                continue
            ks.append(int(part))
    ks = sorted(set(ks))
    if not ks:
        raise SystemExit("Provide at least one k via --k (e.g. --k 1 3 5 10)")
    if any(k <= 0 for k in ks):
        raise SystemExit("All k must be positive integers")
    return ks


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate retrieval metrics against labeled queries (jsonl).")
    p.add_argument("--index-dir", default="output_index", help="Folder with index.faiss + metadata.jsonl + manifest.json")
    p.add_argument("--dataset", required=True, help="JSONL file with queries + relevant_chunk_ids")
    p.add_argument("--k", nargs="+", default=["1,3,5,10"], help="k values, e.g. --k 1 3 5 10 or --k 1,3,5,10")
    p.add_argument("--batch-size", type=int, default=16, help="Embedding batch size")
    p.add_argument("--model-name", default=None, help="Override embedding model name (default from manifest)")
    p.add_argument("--show-per-query", action="store_true", help="Print per-query metrics")
    p.add_argument("--max-queries", type=int, default=None, help="Evaluate only first N queries")
    return p.parse_args()


def main() -> None:
    _configure_utf8_output()
    args = parse_args()
    index_dir = Path(args.index_dir)
    dataset_path = Path(args.dataset)
    ks = parse_k_list(args.k)
    max_k = max(ks)

    manifest = load_manifest(index_dir)
    manifest_model = (manifest.get("config") or {}).get("model_name")
    model_name = args.model_name or manifest_model or "BAAI/bge-m3"

    index_path = index_dir / "index.faiss"
    if not index_path.exists():
        raise SystemExit(f"Missing index file: {index_path}")
    metadata = load_metadata(index_dir)
    index = faiss.read_index(str(index_path))
    if metadata and len(metadata) != index.ntotal:
        raise SystemExit(f"Metadata/index size mismatch: metadata={len(metadata)} vs index.ntotal={index.ntotal}")

    chunk_id_to_row: Dict[str, int] = {}
    for i, row in enumerate(metadata):
        cid = row.get("chunk_id")
        if cid:
            chunk_id_to_row[str(cid)] = i

    examples: List[Dict[str, Any]] = []
    for ex in iter_jsonl(dataset_path):
        if args.max_queries is not None and len(examples) >= args.max_queries:
            break
        q = ex.get("query")
        rel = ex.get("relevant_chunk_ids")
        if not isinstance(q, str) or not q.strip():
            raise SystemExit("Each dataset row must have non-empty string field: query")
        if not isinstance(rel, list) or not all(isinstance(x, str) and x for x in rel):
            raise SystemExit("Each dataset row must have list[str] field: relevant_chunk_ids")
        examples.append({"query": q.strip(), "relevant_chunk_ids": rel})

    if not examples:
        raise SystemExit(f"No examples found in dataset: {dataset_path}")

    queries = [e["query"] for e in examples]
    relevant_sets: List[Set[int]] = []
    unknown_chunk_ids = 0
    for e in examples:
        rel_rows: Set[int] = set()
        for cid in e["relevant_chunk_ids"]:
            ridx = chunk_id_to_row.get(cid)
            if ridx is None:
                unknown_chunk_ids += 1
                continue
            rel_rows.add(ridx)
        relevant_sets.append(rel_rows)

    if unknown_chunk_ids:
        print(f"warning: {unknown_chunk_ids} relevant_chunk_ids were not found in metadata.jsonl")
        print("")

    model = SentenceTransformer(model_name)
    qvecs = embed_queries(model, queries, batch_size=args.batch_size)

    scores, ids = index.search(qvecs, max_k)  # (nq, max_k)

    totals: Dict[str, float] = {}
    counts: Dict[str, int] = {}

    def add(name: str, val: float) -> None:
        totals[name] = totals.get(name, 0.0) + float(val)
        counts[name] = counts.get(name, 0) + 1

    print(f"model_name: {model_name}")
    print(f"index_dir: {index_dir}")
    print(f"dataset: {dataset_path}")
    print(f"num_queries: {len(examples)}")
    print(f"index.ntotal: {index.ntotal} | dim: {index.d}")
    print(f"ks: {ks}")
    print("")

    for qi, q in enumerate(queries):
        rel_rows = relevant_sets[qi]
        retrieved = ids[qi].tolist()

        rels = [1 if (rid in rel_rows) else 0 for rid in retrieved]

        if args.show_per_query:
            print(f"query[{qi+1}]: {q}")
            print(f"  relevant_count: {len(rel_rows)}")

        for k in ks:
            topk_rels = rels[:k]
            hit = 1.0 if any(topk_rels) else 0.0
            retrieved_relevant = float(sum(topk_rels))
            precision = retrieved_relevant / float(k)
            recall = retrieved_relevant / float(len(rel_rows)) if len(rel_rows) > 0 else 0.0

            rr = 0.0
            for rank, r in enumerate(topk_rels, start=1):
                if r:
                    rr = 1.0 / float(rank)
                    break

            ndcg = ndcg_at_k(topk_rels, k=k, num_relevant_total=len(rel_rows))

            add(f"hit@{k}", hit)
            add(f"precision@{k}", precision)
            add(f"recall@{k}", recall)
            add(f"mrr@{k}", rr)
            add(f"ndcg@{k}", ndcg)

            if args.show_per_query:
                print(
                    f"  k={k}: hit={hit:.0f}  p={precision:.3f}  r={recall:.3f}  mrr={rr:.3f}  ndcg={ndcg:.3f}"
                )

        if args.show_per_query:
            print("")

    print("=== AVERAGES ===")
    for k in ks:
        for name in (f"hit@{k}", f"precision@{k}", f"recall@{k}", f"mrr@{k}", f"ndcg@{k}"):
            avg = totals.get(name, 0.0) / float(counts.get(name, 1))
            print(f"{name}: {avg:.4f}")


if __name__ == "__main__":
    main()

