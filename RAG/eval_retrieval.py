#!/usr/bin/env python
import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Literal, Optional, Sequence, Set, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


ConfigName = Literal["semantic_only", "semantic_clause_boost", "semantic_clause_filter"]


CLAUSE_DIEU_RE = re.compile(r"(?:^|[\s,;:()])(?:điều|dieu)\s+([0-9IVXLC]+(?:[.\-][0-9]+)*)", re.IGNORECASE)
CLAUSE_KHOAN_RE = re.compile(r"(?:^|[\s,;:()])(?:khoản|khoan)\s+([0-9]+)", re.IGNORECASE)


@dataclass(frozen=True)
class ClauseSignals:
    dieu: Optional[str] = None
    khoan: Optional[str] = None


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


def _norm_text(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[\t\r\n]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.casefold()


def extract_clause_signals(query: str) -> ClauseSignals:
    qn = _norm_text(query)
    dieu = None
    khoan = None
    md = CLAUSE_DIEU_RE.search(" " + qn + " ")
    if md:
        dieu = md.group(1)
    mk = CLAUSE_KHOAN_RE.search(" " + qn + " ")
    if mk:
        khoan = mk.group(1)
    return ClauseSignals(dieu=dieu, khoan=khoan)


def _make_exact_phrase_re(prefix: str, value: str) -> re.Pattern[str]:
    v = re.escape(_norm_text(value))
    p = _norm_text(prefix)
    if p in {"điều", "dieu"}:
        p_re = r"(?:điều|dieu)"
    elif p in {"khoản", "khoan"}:
        p_re = r"(?:khoản|khoan)"
    else:
        p_re = re.escape(p)
    return re.compile(rf"(?:^|\s){p_re}\s+{v}(?:\s|$)", re.IGNORECASE)


def clause_match(row: Dict[str, Any], signals: ClauseSignals) -> Tuple[bool, Dict[str, bool]]:
    if not signals.dieu and not signals.khoan:
        return False, {"dieu": False, "khoan": False}

    raw_heading = str(row.get("heading") or "")
    raw_text = str(row.get("text") or "")
    hn = _norm_text(f"{raw_heading} {raw_text}".strip())

    matched_dieu = False
    matched_khoan = False

    if signals.dieu:
        dieu_re = _make_exact_phrase_re("điều", signals.dieu)
        matched_dieu = bool(dieu_re.search(hn))
    if signals.khoan:
        khoan_re = _make_exact_phrase_re("khoản", signals.khoan)
        matched_khoan = bool(khoan_re.search(hn))
        if not matched_khoan:
            enum_re = re.compile(rf"(?:^|\n)\s*{re.escape(str(signals.khoan))}\s*[\.\)]", re.MULTILINE)
            matched_khoan = bool(enum_re.search(raw_text))

    any_match = (matched_dieu or not signals.dieu) and (matched_khoan or not signals.khoan)
    return any_match, {"dieu": matched_dieu, "khoan": matched_khoan}


def format_snippet(text: str, limit: int) -> str:
    t = " ".join(str(text).split())
    if len(t) <= limit:
        return t
    return t[: max(0, limit - 3)] + "..."


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def has_valid_citation(result: Dict[str, Any]) -> bool:
    chunk_id = str(result.get("chunk_id") or "").strip()
    source_path = str(result.get("source_path") or "").strip()
    snippet = str(result.get("snippet") or "").strip()
    return bool(chunk_id and source_path and snippet)


def assess_query_evidence(
    *,
    reranked: Sequence[Dict[str, Any]],
    rel_rows: Set[int],
    relevant_chunk_ids: Sequence[str],
    evidence_top_k: int,
    snippet_chars: int,
) -> Dict[str, Any]:
    top_k = max(1, int(evidence_top_k))

    if len(relevant_chunk_ids) <= 0:
        return {
            "status": "NO_GROUND_TRUTH",
            "can_conclude": False,
            "reason": "Query không có nhãn relevant_chunk_ids nên không thể kiểm chứng bằng chứng.",
            "evidence_top_k": top_k,
            "relevant_total": 0,
            "supporting_hits": 0,
            "supporting_citations": [],
        }

    if len(rel_rows) <= 0:
        return {
            "status": "NO_GROUND_TRUTH",
            "can_conclude": False,
            "reason": "Nhãn relevant_chunk_ids không map được sang metadata/index hiện tại.",
            "evidence_top_k": top_k,
            "relevant_total": len(relevant_chunk_ids),
            "supporting_hits": 0,
            "supporting_citations": [],
        }

    supporting: List[Dict[str, Any]] = []
    for rank, row in enumerate(reranked[:top_k], start=1):
        faiss_id = int(row.get("faiss_id", -1))
        if faiss_id not in rel_rows:
            continue

        citation = {
            "rank": int(rank),
            "score": _safe_float(row.get("score"), 0.0),
            "chunk_id": row.get("chunk_id"),
            "heading": row.get("heading"),
            "source_path": row.get("source_path"),
            "snippet": format_snippet(str(row.get("text") or ""), int(snippet_chars)),
        }
        if has_valid_citation(citation):
            supporting.append(citation)

    if supporting:
        return {
            "status": "SUPPORTED",
            "can_conclude": True,
            "reason": "Tìm thấy bằng chứng hợp lệ trong top-k để hỗ trợ kết luận.",
            "evidence_top_k": top_k,
            "relevant_total": len(relevant_chunk_ids),
            "supporting_hits": len(supporting),
            "supporting_citations": supporting,
        }

    return {
        "status": "INSUFFICIENT_EVIDENCE",
        "can_conclude": False,
        "reason": "Không có chunk relevant nào trong cửa sổ bằng chứng top-k.",
        "evidence_top_k": top_k,
        "relevant_total": len(relevant_chunk_ids),
        "supporting_hits": 0,
        "supporting_citations": [],
    }


def build_query_conclusion(evidence_assessment: Dict[str, Any]) -> Dict[str, Any]:
    status = str(evidence_assessment.get("status") or "")
    citations = evidence_assessment.get("supporting_citations") or []

    if status == "SUPPORTED" and citations:
        c0 = citations[0]
        return {
            "status": "CONCLUDED",
            "rule": "no_evidence_no_conclusion",
            "message": (
                "Đủ bằng chứng để kết luận. "
                f"Citation chính: chunk_id={c0.get('chunk_id')} | source={c0.get('source_path')}"
            ),
        }

    if status == "NO_GROUND_TRUTH":
        return {
            "status": "WITHHELD",
            "rule": "no_evidence_no_conclusion",
            "message": "Không có ground-truth hợp lệ nên không kết luận.",
        }

    return {
        "status": "WITHHELD",
        "rule": "no_evidence_no_conclusion",
        "message": "Không đủ bằng chứng nên không kết luận.",
    }


def build_evidence_gate_summary(
    *,
    all_rows: Sequence[Dict[str, Any]],
    configs: Sequence[str],
    min_support_rate: float,
    min_supported_queries: int,
    metric_summary: Dict[str, Any],
    compare_only: bool,
    max_k: int,
) -> Dict[str, Any]:
    per_config: Dict[str, Dict[str, Any]] = {}
    candidates: List[Tuple[Tuple[float, float, float, float, float], str]] = []

    for cfg in configs:
        cfg_rows = [r for r in all_rows if str(r.get("config")) == str(cfg)]

        supported = 0
        insufficient = 0
        no_gt = 0
        for row in cfg_rows:
            evidence = row.get("evidence_assessment") or {}
            status = str(evidence.get("status") or "")
            if status == "SUPPORTED":
                supported += 1
            elif status == "INSUFFICIENT_EVIDENCE":
                insufficient += 1
            else:
                no_gt += 1

        assessed = supported + insufficient
        support_rate = (float(supported) / float(assessed)) if assessed > 0 else 0.0
        gate_pass = (
            assessed > 0
            and supported >= int(min_supported_queries)
            and support_rate >= float(min_support_rate)
        )

        metrics: Dict[str, float] = {}
        if not compare_only:
            overall = ((metric_summary.get(str(cfg)) or {}).get("overall") or {})
            metrics = {
                f"hit@{max_k}": _safe_float(overall.get(f"hit@{max_k}"), 0.0),
                f"mrr@{max_k}": _safe_float(overall.get(f"mrr@{max_k}"), 0.0),
                f"ndcg@{max_k}": _safe_float(overall.get(f"ndcg@{max_k}"), 0.0),
            }

        per_config[str(cfg)] = {
            "total_queries": len(cfg_rows),
            "assessed_queries": assessed,
            "supported_queries": supported,
            "insufficient_queries": insufficient,
            "no_ground_truth_queries": no_gt,
            "support_rate": support_rate,
            "gate_pass": gate_pass,
            "metrics_snapshot": metrics,
        }

        if gate_pass:
            mrr = metrics.get(f"mrr@{max_k}", 0.0)
            ndcg = metrics.get(f"ndcg@{max_k}", 0.0)
            hit = metrics.get(f"hit@{max_k}", 0.0)
            rank_key = (support_rate, float(supported), mrr, ndcg, hit)
            candidates.append((rank_key, str(cfg)))

    if candidates:
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        winner = candidates[0][1]
        if compare_only:
            decision_reason = (
                "Ít nhất một cấu hình vượt ngưỡng bằng chứng; chọn cấu hình có support_rate cao nhất."
            )
        else:
            decision_reason = (
                "Ít nhất một cấu hình vượt ngưỡng bằng chứng; chọn cấu hình có support_rate cao nhất "
                "và metric retrieval tốt nhất."
            )
        final_decision = {
            "status": "CONCLUDED",
            "rule": "no_evidence_no_conclusion",
            "recommended_config": winner,
            "reason": decision_reason,
        }
    else:
        final_decision = {
            "status": "WITHHELD",
            "rule": "no_evidence_no_conclusion",
            "recommended_config": None,
            "reason": (
                "Không có cấu hình nào vượt ngưỡng bằng chứng nên hệ thống không đưa ra kết luận cuối."
            ),
        }

    return {
        "policy": {
            "rule": "no_evidence_no_conclusion",
            "min_support_rate": float(min_support_rate),
            "min_supported_queries": int(min_supported_queries),
            "ranking_metric": f"mrr@{max_k}" if not compare_only else None,
        },
        "per_config": per_config,
        "final_decision": final_decision,
    }


def _stable_argsort_desc(scores: Sequence[float]) -> List[int]:
    return [i for i, _ in sorted(enumerate(scores), key=lambda x: (x[1], -x[0]), reverse=True)]


def rerank_candidates(
    *,
    config: ConfigName,
    cand_ids: Sequence[int],
    cand_scores: Sequence[float],
    metadata: List[Dict[str, Any]],
    signals: ClauseSignals,
    top_k: int,
    boost_dieu: float,
    boost_khoan: float,
    strict_filter: bool,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    need_clause = config != "semantic_only" and (signals.dieu or signals.khoan)

    for base_rank, (idx, base_score) in enumerate(zip(cand_ids, cand_scores), start=1):
        if idx < 0:
            continue
        row = metadata[idx] if metadata else {}
        if need_clause:
            is_match, match_detail = clause_match(row, signals)
        else:
            is_match, match_detail = (False, {"dieu": False, "khoan": False})

        final_score = float(base_score)
        if config == "semantic_clause_boost" and need_clause:
            if signals.dieu and match_detail.get("dieu"):
                final_score += float(boost_dieu)
            if signals.khoan and match_detail.get("khoan"):
                final_score += float(boost_khoan)

        if config == "semantic_clause_filter" and need_clause:
            if not is_match:
                continue

        rows.append(
            {
                "faiss_id": int(idx),
                "base_rank": int(base_rank),
                "base_score": float(base_score),
                "score": float(final_score),
                "chunk_id": row.get("chunk_id"),
                "heading": row.get("heading"),
                "source_path": row.get("source_path"),
                "text": row.get("text") or "",
                "clause_match": bool(is_match),
                "clause_match_detail": match_detail,
            }
        )

    if config == "semantic_clause_filter" and need_clause and not strict_filter and len(rows) < top_k:
        have: Set[int] = {int(r["faiss_id"]) for r in rows}
        for base_rank, (idx, base_score) in enumerate(zip(cand_ids, cand_scores), start=1):
            if idx < 0 or int(idx) in have:
                continue
            row = metadata[idx] if metadata else {}
            rows.append(
                {
                    "faiss_id": int(idx),
                    "base_rank": int(base_rank),
                    "base_score": float(base_score),
                    "score": float(base_score),
                    "chunk_id": row.get("chunk_id"),
                    "heading": row.get("heading"),
                    "source_path": row.get("source_path"),
                    "text": row.get("text") or "",
                    "clause_match": False,
                    "clause_match_detail": {"dieu": False, "khoan": False},
                }
            )
            if len(rows) >= top_k:
                break

    rows = sorted(rows, key=lambda r: (float(r["score"]), float(r["base_score"])), reverse=True)
    return rows[:top_k]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate retrieval metrics against labeled queries (jsonl).")
    p.add_argument("--index-dir", default="output_index", help="Folder with index.faiss + metadata.jsonl + manifest.json")
    p.add_argument("--dataset", required=True, help="JSONL file with queries + relevant_chunk_ids")
    p.add_argument("--k", nargs="+", default=["1,3,5,10"], help="k values, e.g. --k 1 3 5 10 or --k 1,3,5,10")
    p.add_argument("--batch-size", type=int, default=16, help="Embedding batch size")
    p.add_argument("--model-name", default=None, help="Override embedding model name (default from manifest)")
    p.add_argument("--show-per-query", action="store_true", help="Print per-query metrics")
    p.add_argument("--max-queries", type=int, default=None, help="Evaluate only first N queries")
    p.add_argument(
        "--configs",
        nargs="+",
        default=["semantic_only", "semantic_clause_boost", "semantic_clause_filter"],
        choices=["semantic_only", "semantic_clause_boost", "semantic_clause_filter"],
        help="Retrieval configs to compare (default: semantic_only + clause_boost + clause_filter).",
    )
    p.add_argument("--top-k", type=int, default=None, help="How many results to log per query/config (default: max(k))")
    p.add_argument("--oversample-factor", type=int, default=50, help="Candidates = max(k) * oversample-factor (min 50)")
    p.add_argument("--snippet-chars", type=int, default=240, help="Snippet length for logging/report")
    p.add_argument("--boost-dieu", type=float, default=0.12, help="Additive boost if matched Điều X (clause_boost)")
    p.add_argument("--boost-khoan", type=float, default=0.12, help="Additive boost if matched Khoản Y (clause_boost)")
    p.add_argument("--strict-filter", action="store_true", help="If set, clause_filter returns <top-k> if not enough matches")
    p.add_argument(
        "--compare-only",
        action="store_true",
        help="Chỉ chạy retrieval so sánh và xuất log top-k (không in/tính metrics, không summary_metrics).",
    )
    p.add_argument(
        "--out-dir",
        default="retrieval_runs",
        help="Write JSONL logs + markdown report under this folder (default: retrieval_runs/).",
    )
    p.add_argument(
        "--evidence-top-k",
        type=int,
        default=3,
        help="Cửa sổ top-k dùng để kiểm chứng bằng chứng cho tầng kết luận cuối.",
    )
    p.add_argument(
        "--min-support-rate",
        type=float,
        default=0.7,
        help="Tỉ lệ query có bằng chứng tối thiểu để cho phép kết luận theo config.",
    )
    p.add_argument(
        "--min-supported-queries",
        type=int,
        default=1,
        help="Số query có bằng chứng tối thiểu để cho phép kết luận theo config.",
    )
    return p.parse_args()


def main() -> None:
    _configure_utf8_output()
    args = parse_args()
    if int(args.evidence_top_k) <= 0:
        raise SystemExit("--evidence-top-k must be > 0")
    if not (0.0 <= float(args.min_support_rate) <= 1.0):
        raise SystemExit("--min-support-rate must be in [0, 1]")
    if int(args.min_supported_queries) <= 0:
        raise SystemExit("--min-supported-queries must be > 0")

    index_dir = Path(args.index_dir)
    dataset_path = Path(args.dataset)
    ks = parse_k_list(args.k)
    max_k = max(ks)
    log_top_k = int(args.top_k or max_k)
    oversample = max(int(max_k) * int(args.oversample_factor), 50)

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
        group = ex.get("group")
        if not isinstance(q, str) or not q.strip():
            raise SystemExit("Each dataset row must have non-empty string field: query")
        if not isinstance(rel, list) or not all(isinstance(x, str) and x for x in rel):
            raise SystemExit("Each dataset row must have list[str] field: relevant_chunk_ids")
        if group is not None and not isinstance(group, str):
            raise SystemExit("If provided, dataset field group must be a string")
        examples.append({"query": q.strip(), "relevant_chunk_ids": rel, "group": (group or "ungrouped")})

    if not examples:
        raise SystemExit(f"No examples found in dataset: {dataset_path}")

    queries = [e["query"] for e in examples]
    groups = [e.get("group") or "ungrouped" for e in examples]
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

    base_scores, base_ids = index.search(qvecs, oversample)  # (nq, oversample)

    print(f"model_name: {model_name}")
    print(f"index_dir: {index_dir}")
    print(f"dataset: {dataset_path}")
    print(f"num_queries: {len(examples)}")
    print(f"index.ntotal: {index.ntotal} | dim: {index.d}")
    if not args.compare_only:
        print(f"ks: {ks}")
    print(f"configs: {args.configs}")
    print("")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir) / run_id if args.out_dir else None
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)

    def eval_one_config(config: ConfigName) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]], List[Dict[str, Any]]]:
        totals: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        group_totals: Dict[str, Dict[str, float]] = {}
        group_counts: Dict[str, Dict[str, int]] = {}

        def add(name: str, val: float) -> None:
            totals[name] = totals.get(name, 0.0) + float(val)
            counts[name] = counts.get(name, 0) + 1

        def add_group(group: str, name: str, val: float) -> None:
            gt = group_totals.setdefault(group, {})
            gc = group_counts.setdefault(group, {})
            gt[name] = gt.get(name, 0.0) + float(val)
            gc[name] = gc.get(name, 0) + 1

        rows_out: List[Dict[str, Any]] = []

        for qi, q in enumerate(queries):
            rel_rows = relevant_sets[qi]
            cand_ids = base_ids[qi].tolist()
            cand_scores = base_scores[qi].tolist()
            signals = extract_clause_signals(q)

            reranked = rerank_candidates(
                config=config,
                cand_ids=cand_ids,
                cand_scores=cand_scores,
                metadata=metadata,
                signals=signals,
                top_k=log_top_k,
                boost_dieu=float(args.boost_dieu),
                boost_khoan=float(args.boost_khoan),
                strict_filter=bool(args.strict_filter),
            )
            retrieved_rows = [int(r["faiss_id"]) for r in reranked]
            rels = [1 if (rid in rel_rows) else 0 for rid in retrieved_rows]

            if args.show_per_query and not args.compare_only:
                print(f"config: {config}")
                print(f"query[{qi+1}]: {q}")
                print(f"  group: {groups[qi]}")
                print(f"  clause_signals: dieu={signals.dieu!r}  khoan={signals.khoan!r}")
                print(f"  relevant_count: {len(rel_rows)}")

            if not args.compare_only:
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

                    grp = groups[qi]
                    add_group(grp, f"hit@{k}", hit)
                    add_group(grp, f"precision@{k}", precision)
                    add_group(grp, f"recall@{k}", recall)
                    add_group(grp, f"mrr@{k}", rr)
                    add_group(grp, f"ndcg@{k}", ndcg)

                    if args.show_per_query:
                        print(
                            f"  k={k}: hit={hit:.0f}  p={precision:.3f}  r={recall:.3f}  mrr={rr:.3f}  ndcg={ndcg:.3f}"
                        )

                if args.show_per_query:
                    print("")

            results_out = []
            for rank, r in enumerate(reranked, start=1):
                results_out.append(
                    {
                        "rank": int(rank),
                        "score": float(r["score"]),
                        "chunk_id": r.get("chunk_id"),
                        "heading": r.get("heading"),
                        "source_path": r.get("source_path"),
                        "snippet": format_snippet(r.get("text") or "", int(args.snippet_chars)),
                    }
                )

            evidence_assessment = assess_query_evidence(
                reranked=reranked,
                rel_rows=rel_rows,
                relevant_chunk_ids=examples[qi]["relevant_chunk_ids"],
                evidence_top_k=int(args.evidence_top_k),
                snippet_chars=int(args.snippet_chars),
            )

            rows_out.append(
                {
                    "run_id": run_id,
                    "config": config,
                    "group": groups[qi],
                    "query": q,
                    "clause_signals": {"dieu": signals.dieu, "khoan": signals.khoan},
                    "relevant_chunk_ids": examples[qi]["relevant_chunk_ids"],
                    "evidence_assessment": evidence_assessment,
                    "final_conclusion": build_query_conclusion(evidence_assessment),
                    "results": results_out,
                }
            )

        avgs: Dict[str, float] = {}
        by_group: Dict[str, Dict[str, float]] = {}
        if not args.compare_only:
            for k in ks:
                for name in (f"hit@{k}", f"precision@{k}", f"recall@{k}", f"mrr@{k}", f"ndcg@{k}"):
                    avgs[name] = totals.get(name, 0.0) / float(counts.get(name, 1))
            for grp, gt in group_totals.items():
                by_group[grp] = {}
                for k in ks:
                    for name in (f"hit@{k}", f"precision@{k}", f"recall@{k}", f"mrr@{k}", f"ndcg@{k}"):
                        by_group[grp][name] = gt.get(name, 0.0) / float(group_counts.get(grp, {}).get(name, 1))
        return avgs, by_group, rows_out

    all_summaries: Dict[str, Any] = {}
    all_rows: List[Dict[str, Any]] = []

    for config in args.configs:
        avgs, by_group, rows_out = eval_one_config(config=config)  # type: ignore[arg-type]
        all_summaries[str(config)] = {"overall": avgs, "by_group": by_group}
        all_rows.extend(rows_out)

    evidence_summary = build_evidence_gate_summary(
        all_rows=all_rows,
        configs=[str(c) for c in args.configs],
        min_support_rate=float(args.min_support_rate),
        min_supported_queries=int(args.min_supported_queries),
        metric_summary=all_summaries,
        compare_only=bool(args.compare_only),
        max_k=int(max_k),
    )

    if not args.compare_only:
        print("=== AVERAGES (per config) ===")
        for config in args.configs:
            print(f"\n[{config}]")
            for k in ks:
                for name in (f"hit@{k}", f"precision@{k}", f"recall@{k}", f"mrr@{k}", f"ndcg@{k}"):
                    print(f"{name}: {all_summaries[str(config)]['overall'][name]:.4f}")

    if out_dir is not None:
        (out_dir / "run_config.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "index_dir": str(index_dir),
                    "dataset": str(dataset_path),
                    "model_name": model_name,
                    "ks": ks if not args.compare_only else None,
                    "configs": args.configs,
                    "log_top_k": log_top_k,
                    "oversample": oversample,
                    "snippet_chars": int(args.snippet_chars),
                    "boost_dieu": float(args.boost_dieu),
                    "boost_khoan": float(args.boost_khoan),
                    "strict_filter": bool(args.strict_filter),
                    "compare_only": bool(args.compare_only),
                    "evidence_top_k": int(args.evidence_top_k),
                    "min_support_rate": float(args.min_support_rate),
                    "min_supported_queries": int(args.min_supported_queries),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        if not args.compare_only:
            (out_dir / "summary_metrics.json").write_text(
                json.dumps(all_summaries, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        (out_dir / "evidence_summary.json").write_text(
            json.dumps(evidence_summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        with (out_dir / "retrieval_logs.jsonl").open("w", encoding="utf-8") as f:
            for row in all_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        report_lines: List[str] = []
        report_lines.append("# Báo cáo so sánh retrieval\n")
        report_lines.append(f"- run_id: `{run_id}`")
        report_lines.append(f"- model_name: `{model_name}`")
        report_lines.append(f"- index_dir: `{index_dir}`")
        report_lines.append(f"- dataset: `{dataset_path}`")
        report_lines.append(f"- configs: `{', '.join(args.configs)}`")
        if not args.compare_only:
            report_lines.append(f"- ks: `{', '.join(str(k) for k in ks)}`")
        report_lines.append("")

        report_lines.append("## Tầng kết luận cuối (enforce: không bằng chứng thì không kết luận)\n")
        report_lines.append(f"- evidence_top_k: `{int(args.evidence_top_k)}`")
        report_lines.append(f"- min_support_rate: `{float(args.min_support_rate):.2f}`")
        report_lines.append(f"- min_supported_queries: `{int(args.min_supported_queries)}`")
        report_lines.append("")
        for cfg in args.configs:
            cfg_stats = (evidence_summary.get("per_config") or {}).get(str(cfg), {})
            report_lines.append(
                f"- `{cfg}`: gate_pass=`{cfg_stats.get('gate_pass')}` | "
                f"supported/assessed=`{cfg_stats.get('supported_queries')}/{cfg_stats.get('assessed_queries')}` | "
                f"support_rate=`{_safe_float(cfg_stats.get('support_rate'), 0.0):.3f}`"
            )
        final_decision = evidence_summary.get("final_decision") or {}
        if final_decision.get("status") == "CONCLUDED":
            report_lines.append(
                f"- Kết luận cuối: chọn config `{final_decision.get('recommended_config')}`."
            )
        else:
            report_lines.append(
                f"- Kết luận cuối: KHÔNG KẾT LUẬN. Lý do: {final_decision.get('reason')}"
            )
        report_lines.append("")

        report_lines.append("## Kết quả retrieval top-k (log để làm citation sau)\n")
        report_lines.append("Mỗi kết quả gồm: `rank, score, chunk_id, heading, source_path, snippet`.\n")

        by_query: Dict[str, List[Dict[str, Any]]] = {}
        for row in all_rows:
            key = f"{row.get('group')}||{row.get('query')}"
            by_query.setdefault(key, []).append(row)

        for key in sorted(by_query.keys()):
            grp, q = key.split("||", 1)
            report_lines.append(f"### {q}\n")
            report_lines.append(f"- group: `{grp}`")
            report_lines.append(f"- clause_signals: `{by_query[key][0].get('clause_signals')}`")
            report_lines.append("")
            for row in sorted(by_query[key], key=lambda r: str(r.get("config"))):
                report_lines.append(f"#### Config: `{row.get('config')}`\n")
                for r in row.get("results", [])[: min(3, log_top_k)]:
                    report_lines.append(
                        f"- rank={r.get('rank')} score={r.get('score'):.4f} | "
                        f"chunk_id=`{r.get('chunk_id')}` | heading=`{r.get('heading')}` | "
                        f"source=`{r.get('source_path')}`\n  - snippet: {r.get('snippet')}"
                    )
                evidence = row.get("evidence_assessment") or {}
                report_lines.append(
                    f"- evidence_status=`{evidence.get('status')}` | "
                    f"supporting_hits=`{evidence.get('supporting_hits')}` | "
                    f"evidence_top_k=`{evidence.get('evidence_top_k')}`"
                )
                report_lines.append(
                    f"- final_conclusion: {(row.get('final_conclusion') or {}).get('message')}"
                )
                supports = evidence.get("supporting_citations") or []
                if supports:
                    top_support = supports[0]
                    report_lines.append(
                        f"- top_evidence: rank={top_support.get('rank')} | chunk_id=`{top_support.get('chunk_id')}` | "
                        f"source=`{top_support.get('source_path')}`"
                    )
                report_lines.append("")

        (out_dir / "report.md").write_text("\n".join(report_lines).strip() + "\n", encoding="utf-8")

        conclusion_lines: List[str] = []
        conclusion_lines.append("# Kết luận tự động (Evidence Gate)\n")
        conclusion_lines.append(
            "Nguyên tắc áp dụng: **không bằng chứng -> không kết luận**."
        )
        conclusion_lines.append("")
        for cfg in args.configs:
            cfg_stats = (evidence_summary.get("per_config") or {}).get(str(cfg), {})
            conclusion_lines.append(
                f"- {cfg}: gate_pass={cfg_stats.get('gate_pass')}, "
                f"supported/assessed={cfg_stats.get('supported_queries')}/{cfg_stats.get('assessed_queries')}, "
                f"support_rate={_safe_float(cfg_stats.get('support_rate'), 0.0):.3f}"
            )
        conclusion_lines.append("")
        final_status = (evidence_summary.get("final_decision") or {}).get("status")
        final_cfg = (evidence_summary.get("final_decision") or {}).get("recommended_config")
        final_reason = (evidence_summary.get("final_decision") or {}).get("reason")
        if final_status == "CONCLUDED":
            conclusion_lines.append(f"Kết luận cuối: chọn cấu hình {final_cfg}.")
        else:
            conclusion_lines.append("Kết luận cuối: KHÔNG KẾT LUẬN.")
        conclusion_lines.append(f"Lý do: {final_reason}")

        (out_dir / "final_conclusion.md").write_text(
            "\n".join(conclusion_lines).strip() + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()

