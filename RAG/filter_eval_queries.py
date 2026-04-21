#!/usr/bin/env python
"""
Lọc và cải thiện bộ eval queries auto-generated (tuần 11).

Loại bỏ:
  - Query < 5 ký tự (vô nghĩa: "Công", "Tổng", "Thiết", ...)
  - Query trùng lặp
  - Query chỉ chứa số

Usage:
    python filter_eval_queries.py --input eval_queries.auto.jsonl --output eval_queries.auto.filtered.jsonl
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Set


def _configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def filter_queries(
    input_path: Path,
    output_path: Path,
    min_chars: int = 5,
    min_words: int = 2,
) -> Dict[str, int]:
    """Lọc queries, trả về thống kê."""
    stats = {
        "total_input": 0,
        "removed_short": 0,
        "removed_duplicate": 0,
        "removed_numeric_only": 0,
        "total_output": 0,
    }

    queries: List[dict] = []
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            queries.append(json.loads(line))

    stats["total_input"] = len(queries)

    # Pass 1: Filter
    seen_queries: Set[str] = set()
    filtered: List[dict] = []

    for entry in queries:
        query = entry.get("query", "").strip()

        # Loại query quá ngắn
        if len(query) < min_chars:
            stats["removed_short"] += 1
            continue

        # Loại query ít từ
        words = query.split()
        if len(words) < min_words:
            stats["removed_short"] += 1
            continue

        # Loại query chỉ chứa số/dấu
        alpha_chars = [c for c in query if c.isalpha()]
        if len(alpha_chars) < 3:
            stats["removed_numeric_only"] += 1
            continue

        # Loại query trùng lặp (case-insensitive)
        query_lower = query.lower()
        if query_lower in seen_queries:
            stats["removed_duplicate"] += 1
            continue
        seen_queries.add(query_lower)

        filtered.append(entry)

    stats["total_output"] = len(filtered)

    # Write output
    with output_path.open("w", encoding="utf-8") as f:
        for entry in filtered:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return stats


def main() -> None:
    _configure_utf8_output()

    parser = argparse.ArgumentParser(description="Filter eval queries — remove low-quality entries.")
    parser.add_argument("--input", default="eval_queries.auto.jsonl", help="Input JSONL file")
    parser.add_argument("--output", default="eval_queries.auto.filtered.jsonl", help="Output JSONL file")
    parser.add_argument("--min-chars", type=int, default=5, help="Minimum query length in characters")
    parser.add_argument("--min-words", type=int, default=2, help="Minimum query length in words")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    stats = filter_queries(input_path, output_path, args.min_chars, args.min_words)

    print("=== Query Filtering Results ===")
    print(f"Input:            {stats['total_input']} queries")
    print(f"Removed (short):  {stats['removed_short']}")
    print(f"Removed (dup):    {stats['removed_duplicate']}")
    print(f"Removed (numeric):{stats['removed_numeric_only']}")
    print(f"Output:           {stats['total_output']} queries")
    print(f"Reduction:        {stats['total_input'] - stats['total_output']} removed "
          f"({(stats['total_input'] - stats['total_output']) / max(stats['total_input'], 1) * 100:.1f}%)")
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    main()
