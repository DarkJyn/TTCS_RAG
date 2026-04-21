#!/usr/bin/env python
"""
Đánh giá comparison engine trên tập dữ liệu mẫu có ground-truth.

Đo precision, recall, F1 phát hiện thay đổi + type accuracy.

Usage:
    python eval_comparison.py --gt eval_comparison_gt.jsonl --pairs-dir test_pairs --out-dir comparison_runs
"""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from compare_engine import compare_documents, DiffType, summary_stats, _heading_key


def _configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


@dataclass
class PairResult:
    pair_id: str
    doc1: str
    doc2: str
    stats: Dict[str, int]
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    type_accuracy: float
    details: List[Dict[str, Any]]


def _normalize_heading_key(heading: Optional[str]) -> str:
    """Chuẩn hóa heading thành key để so sánh — dùng chung logic với compare_engine."""
    return _heading_key(heading)


def evaluate_one_pair(
    doc1_text: str,
    doc2_text: str,
    expected_diffs: List[Dict[str, str]],
) -> PairResult:
    """Đánh giá 1 cặp tài liệu."""
    # Chạy comparison engine
    results = compare_documents(doc1_text, doc2_text)
    stats = summary_stats(results)

    # Build predicted set (chỉ lấy thay đổi, không lấy UNCHANGED)
    predicted: Dict[str, str] = {}
    for r in results:
        if r.diff_type != DiffType.UNCHANGED:
            key = _normalize_heading_key(r.heading)
            predicted[key] = r.diff_type.value

    # Build expected set
    expected: Dict[str, str] = {}
    for e in expected_diffs:
        key = _normalize_heading_key(e.get("heading"))
        expected[key] = e.get("diff_type", "").lower()

    # Tính metrics
    tp = 0
    fp = 0
    correct_type = 0
    details: List[Dict[str, Any]] = []

    for key, pred_type in predicted.items():
        if key in expected:
            tp += 1
            type_correct = pred_type == expected[key]
            if type_correct:
                correct_type += 1
            details.append({
                "heading_key": key,
                "predicted_type": pred_type,
                "expected_type": expected[key],
                "match": True,
                "type_correct": type_correct,
            })
        else:
            fp += 1
            details.append({
                "heading_key": key,
                "predicted_type": pred_type,
                "expected_type": None,
                "match": False,
                "type_correct": False,
                "note": "false_positive",
            })

    # FN: có trong expected nhưng không có trong predicted
    fn = 0
    for key, exp_type in expected.items():
        if key not in predicted:
            fn += 1
            details.append({
                "heading_key": key,
                "predicted_type": None,
                "expected_type": exp_type,
                "match": False,
                "type_correct": False,
                "note": "false_negative",
            })

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    type_acc = correct_type / tp if tp > 0 else 0.0

    return PairResult(
        pair_id="",
        doc1="",
        doc2="",
        stats=stats,
        tp=tp,
        fp=fp,
        fn=fn,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        type_accuracy=round(type_acc, 4),
        details=details,
    )


def load_gt(gt_path: Path) -> List[Dict[str, Any]]:
    """Đọc ground-truth JSONL."""
    data: List[Dict[str, Any]] = []
    with gt_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON on line {i} of {gt_path}: {exc}") from exc
    return data


def read_doc(path: Path) -> str:
    """Đọc tài liệu text."""
    return path.read_text(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate comparison engine against ground-truth pairs.")
    p.add_argument("--gt", required=True, help="JSONL file with ground-truth (pair_id, doc1, doc2, expected_diffs)")
    p.add_argument("--pairs-dir", default="test_pairs", help="Directory containing test document pairs")
    p.add_argument("--out-dir", default="comparison_runs", help="Output directory for results")
    return p.parse_args()


def main() -> None:
    _configure_utf8_output()
    args = parse_args()

    gt_path = Path(args.gt)
    pairs_dir = Path(args.pairs_dir)
    out_base = Path(args.out_dir)

    if not gt_path.exists():
        raise SystemExit(f"Ground-truth file not found: {gt_path}")
    if not pairs_dir.exists():
        raise SystemExit(f"Pairs directory not found: {pairs_dir}")

    gt_data = load_gt(gt_path)
    if not gt_data:
        raise SystemExit("No ground-truth entries found")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = out_base / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Evaluation run: {run_id}")
    print(f"Ground-truth: {gt_path} ({len(gt_data)} pairs)")
    print(f"Pairs dir: {pairs_dir}")
    print()

    all_results: List[Dict[str, Any]] = []
    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_correct_type = 0

    for entry in gt_data:
        pair_id = entry.get("pair_id", "unknown")
        doc1_name = entry.get("doc1", "")
        doc2_name = entry.get("doc2", "")
        expected_diffs = entry.get("expected_diffs", [])

        doc1_path = pairs_dir / doc1_name
        doc2_path = pairs_dir / doc2_name

        if not doc1_path.exists():
            print(f"  SKIP {pair_id}: {doc1_path} not found")
            continue
        if not doc2_path.exists():
            print(f"  SKIP {pair_id}: {doc2_path} not found")
            continue

        doc1_text = read_doc(doc1_path)
        doc2_text = read_doc(doc2_path)

        result = evaluate_one_pair(doc1_text, doc2_text, expected_diffs)
        result.pair_id = pair_id
        result.doc1 = doc1_name
        result.doc2 = doc2_name

        total_tp += result.tp
        total_fp += result.fp
        total_fn += result.fn
        total_correct_type += sum(1 for d in result.details if d.get("type_correct"))

        print(f"  {pair_id}: P={result.precision:.3f} R={result.recall:.3f} F1={result.f1:.3f} TypeAcc={result.type_accuracy:.3f}")
        print(f"    TP={result.tp} FP={result.fp} FN={result.fn} | Stats: {result.stats}")

        all_results.append({
            "pair_id": pair_id,
            "doc1": doc1_name,
            "doc2": doc2_name,
            "stats": result.stats,
            "tp": result.tp,
            "fp": result.fp,
            "fn": result.fn,
            "precision": result.precision,
            "recall": result.recall,
            "f1": result.f1,
            "type_accuracy": result.type_accuracy,
            "details": result.details,
        })

    # Aggregate metrics
    macro_precision = sum(r["precision"] for r in all_results) / len(all_results) if all_results else 0.0
    macro_recall = sum(r["recall"] for r in all_results) / len(all_results) if all_results else 0.0
    macro_f1 = sum(r["f1"] for r in all_results) / len(all_results) if all_results else 0.0

    micro_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = (2 * micro_precision * micro_recall / (micro_precision + micro_recall)) if (micro_precision + micro_recall) > 0 else 0.0
    overall_type_acc = total_correct_type / total_tp if total_tp > 0 else 0.0

    summary = {
        "run_id": run_id,
        "num_pairs": len(all_results),
        "macro": {
            "precision": round(macro_precision, 4),
            "recall": round(macro_recall, 4),
            "f1": round(macro_f1, 4),
        },
        "micro": {
            "precision": round(micro_precision, 4),
            "recall": round(micro_recall, 4),
            "f1": round(micro_f1, 4),
        },
        "type_accuracy": round(overall_type_acc, 4),
        "totals": {
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
        },
    }

    print()
    print("=== AGGREGATE RESULTS ===")
    print(f"Pairs evaluated: {len(all_results)}")
    print(f"Macro: P={macro_precision:.4f}  R={macro_recall:.4f}  F1={macro_f1:.4f}")
    print(f"Micro: P={micro_precision:.4f}  R={micro_recall:.4f}  F1={micro_f1:.4f}")
    print(f"Type accuracy: {overall_type_acc:.4f}")
    print(f"Totals: TP={total_tp}  FP={total_fp}  FN={total_fn}")

    # Write outputs
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (out_dir / "results.jsonl").open("w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Generate markdown report
    report_lines = [
        "# Báo cáo đánh giá Comparison Engine\n",
        f"- run_id: `{run_id}`",
        f"- ground_truth: `{gt_path}`",
        f"- pairs_dir: `{pairs_dir}`",
        f"- num_pairs: `{len(all_results)}`",
        "",
        "## Kết quả tổng hợp\n",
        "| Metric | Macro | Micro |",
        "|---|---|---|",
        f"| Precision | {macro_precision:.4f} | {micro_precision:.4f} |",
        f"| Recall | {macro_recall:.4f} | {micro_recall:.4f} |",
        f"| F1 | {macro_f1:.4f} | {micro_f1:.4f} |",
        "",
        f"- Type accuracy: `{overall_type_acc:.4f}`",
        f"- Totals: TP=`{total_tp}` FP=`{total_fp}` FN=`{total_fn}`",
        "",
        "## Kết quả theo cặp\n",
    ]

    for r in all_results:
        report_lines.append(f"### {r['pair_id']}\n")
        report_lines.append(f"- doc1: `{r['doc1']}` | doc2: `{r['doc2']}`")
        report_lines.append(f"- P={r['precision']:.4f} R={r['recall']:.4f} F1={r['f1']:.4f} TypeAcc={r['type_accuracy']:.4f}")
        report_lines.append(f"- Stats: {r['stats']}")
        report_lines.append("")

    (out_dir / "report.md").write_text(
        "\n".join(report_lines).strip() + "\n",
        encoding="utf-8",
    )

    print(f"\nResults written to: {out_dir}")


if __name__ == "__main__":
    main()
