#!/usr/bin/env python
"""
So sánh hai tài liệu pháp lý theo cấu trúc Điều / Khoản.
Phát hiện: ADDED, REMOVED, MODIFIED, UNCHANGED.
"""

import difflib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from rag_pipeline import normalize_text, HEADING_RE


class DiffType(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class InlineDiff:
    tag: str          # "equal", "insert", "delete", "replace"
    old_text: str
    new_text: str


@dataclass
class DiffItem:
    heading: Optional[str]
    diff_type: DiffType
    old_text: str
    new_text: str
    similarity: float
    inline_diffs: List[InlineDiff] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "heading": self.heading,
            "diff_type": self.diff_type.value,
            "old_text": self.old_text,
            "new_text": self.new_text,
            "similarity": round(self.similarity, 4),
            "inline_diffs": [
                {"tag": d.tag, "old_text": d.old_text, "new_text": d.new_text}
                for d in self.inline_diffs
            ],
        }


def _split_into_sections(text: str) -> List[Tuple[Optional[str], str]]:
    """Chia văn bản thành danh sách (heading, body)."""
    lines = text.split("\n")
    sections: List[Tuple[Optional[str], str]] = []
    current_heading: Optional[str] = None
    current_lines: List[str] = []

    def flush():
        if not current_lines:
            return
        body = "\n".join(current_lines).strip()
        if body:
            sections.append((current_heading, body))

    for line in lines:
        stripped = line.strip()
        if not stripped:
            current_lines.append("")
            continue
        if HEADING_RE.match(stripped):
            flush()
            current_heading = stripped
            current_lines = [stripped]
        else:
            current_lines.append(stripped)

    flush()
    return sections


def _heading_key(heading: Optional[str]) -> str:
    """Tạo key chuẩn hóa từ heading để matching."""
    if not heading:
        return "__preamble__"
    h = heading.lower().strip()
    h = re.sub(r"\s+", " ", h)
    numbers = re.findall(r"\d+", h)
    prefix_match = re.match(r"(điều|dieu|khoản|khoan|mục|muc)", h, re.IGNORECASE)
    prefix = prefix_match.group(1) if prefix_match else ""
    return f"{prefix}_{'.'.join(numbers)}" if numbers else h[:60]


def _compute_inline_diffs(old_text: str, new_text: str) -> List[InlineDiff]:
    """Tính diff chi tiết inline giữa 2 đoạn text."""
    sm = difflib.SequenceMatcher(None, old_text.split(), new_text.split())
    diffs: List[InlineDiff] = []
    old_words = old_text.split()
    new_words = new_text.split()

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        old_part = " ".join(old_words[i1:i2])
        new_part = " ".join(new_words[j1:j2])
        diffs.append(InlineDiff(tag=tag, old_text=old_part, new_text=new_part))

    return diffs


def compare_documents(doc1_text: str, doc2_text: str) -> List[DiffItem]:
    """
    So sánh 2 tài liệu, trả về danh sách DiffItem.
    doc1 = tài liệu cũ (bản gốc), doc2 = tài liệu mới (bản sửa).
    """
    text1 = normalize_text(doc1_text)
    text2 = normalize_text(doc2_text)

    sections1 = _split_into_sections(text1)
    sections2 = _split_into_sections(text2)

    # Build lookup theo heading key
    map1: Dict[str, Tuple[Optional[str], str]] = {}
    order1: List[str] = []
    for heading, body in sections1:
        key = _heading_key(heading)
        map1[key] = (heading, body)
        order1.append(key)

    map2: Dict[str, Tuple[Optional[str], str]] = {}
    order2: List[str] = []
    for heading, body in sections2:
        key = _heading_key(heading)
        map2[key] = (heading, body)
        order2.append(key)

    all_keys_ordered: List[str] = []
    seen = set()
    for k in order1 + order2:
        if k not in seen:
            all_keys_ordered.append(k)
            seen.add(k)

    results: List[DiffItem] = []

    for key in all_keys_ordered:
        in_old = key in map1
        in_new = key in map2

        if in_old and not in_new:
            heading, body = map1[key]
            results.append(DiffItem(
                heading=heading,
                diff_type=DiffType.REMOVED,
                old_text=body,
                new_text="",
                similarity=0.0,
            ))
        elif not in_old and in_new:
            heading, body = map2[key]
            results.append(DiffItem(
                heading=heading,
                diff_type=DiffType.ADDED,
                old_text="",
                new_text=body,
                similarity=0.0,
            ))
        else:
            heading1, body1 = map1[key]
            heading2, body2 = map2[key]
            heading = heading2 or heading1

            ratio = difflib.SequenceMatcher(None, body1, body2).ratio()

            if ratio >= 0.98:
                results.append(DiffItem(
                    heading=heading,
                    diff_type=DiffType.UNCHANGED,
                    old_text=body1,
                    new_text=body2,
                    similarity=ratio,
                ))
            else:
                inline = _compute_inline_diffs(body1, body2)
                results.append(DiffItem(
                    heading=heading,
                    diff_type=DiffType.MODIFIED,
                    old_text=body1,
                    new_text=body2,
                    similarity=ratio,
                    inline_diffs=inline,
                ))

    return results


def summary_stats(diffs: List[DiffItem]) -> dict:
    """Thống kê tổng quát các thay đổi."""
    stats = {"total": len(diffs), "added": 0, "removed": 0, "modified": 0, "unchanged": 0}
    for d in diffs:
        stats[d.diff_type.value] += 1
    return stats
