#!/usr/bin/env python
"""
So sánh hai tài liệu pháp lý theo cấu trúc Điều / Khoản.
Phát hiện: ADDED, REMOVED, MODIFIED, UNCHANGED.

Tuần 11 — Cải tiến:
  - Giảm similarity threshold (0.98 → 0.85) để phát hiện MODIFIED.
  - Thêm character-level diff count cho detection chính xác hơn.
  - Merge broken headings (Điều\n11. → Điều 11.) trước khi split.
  - Heading key normalization cải thiện.
"""

import difflib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from rag_pipeline import normalize_text, HEADING_RE


# ── Threshold defaults ───────────────────────────────────────────────────
DEFAULT_SIMILARITY_THRESHOLD = 0.85   # Tuần 10: 0.98 — quá lỏng, miss 100% MODIFIED
MIN_CHANGED_CHARS = 2                 # Tối thiểu 2 ký tự thay đổi để đánh MODIFIED


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


# ── Broken heading merge (tuần 11) ──────────────────────────────────────

# Pattern: dòng chỉ chứa prefix heading (Điều/Khoản/Mục/Chương/Phần)
_HEADING_PREFIX_ONLY_RE = re.compile(
    r"^(Điều|Dieu|Khoản|Khoan|Mục|Muc|Chương|Chuong|Phần|Phan)\s*$",
    re.IGNORECASE,
)
# Pattern: dòng tiếp theo bắt đầu bằng số (phần còn lại của heading bị tách)
_HEADING_NUMBER_START_RE = re.compile(r"^\s*([0-9IVXLC]+)")


def _merge_broken_headings(text: str) -> str:
    """
    Ghép heading bị tách qua nhiều dòng.
    Ví dụ: 'Điều\\n11. Nội dung' → 'Điều 11. Nội dung'
    """
    lines = text.split("\n")
    merged: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Kiểm tra nếu dòng hiện tại chỉ chứa prefix heading
        if _HEADING_PREFIX_ONLY_RE.match(stripped):
            # Tìm dòng tiếp theo có nội dung
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            if j < len(lines) and _HEADING_NUMBER_START_RE.match(lines[j].strip()):
                # Merge: prefix + " " + dòng tiếp
                merged_line = stripped + " " + lines[j].strip()
                merged.append(merged_line)
                i = j + 1
                continue

        merged.append(line)
        i += 1

    return "\n".join(merged)


def _split_into_sections(text: str) -> List[Tuple[Optional[str], str]]:
    """Chia văn bản thành danh sách (heading, body)."""
    # Tuần 11: merge broken headings trước khi split
    text = _merge_broken_headings(text)

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
    """
    Tạo key chuẩn hóa từ heading để matching.
    Tuần 11: cải thiện normalize — strip trailing description, handle multi-word.
    """
    if not heading:
        return "__preamble__"
    h = heading.lower().strip()
    # Normalize whitespace (bao gồm newline)
    h = re.sub(r"\s+", " ", h)
    # Tìm prefix
    prefix_match = re.match(
        r"(điều|dieu|khoản|khoan|mục|muc|chương|chuong|phần|phan)",
        h,
        re.IGNORECASE,
    )
    prefix = prefix_match.group(1) if prefix_match else ""
    # Tìm số — chỉ lấy số đầu tiên ngay sau prefix
    numbers = re.findall(r"\d+", h)
    if numbers:
        return f"{prefix}_{'.'.join(numbers[:2])}"  # Tối đa 2 level (vd: Khoản 3 Điều 5)
    return h[:60]


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


def _count_changed_chars(old_text: str, new_text: str) -> int:
    """
    Đếm số ký tự thực sự thay đổi giữa 2 text (tuần 11).
    Dùng SequenceMatcher trên character level để đếm chính xác.
    """
    sm = difflib.SequenceMatcher(None, old_text, new_text)
    changed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            changed += max(i2 - i1, j2 - j1)
    return changed


def compare_documents(
    doc1_text: str,
    doc2_text: str,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> List[DiffItem]:
    """
    So sánh 2 tài liệu, trả về danh sách DiffItem.
    doc1 = tài liệu cũ (bản gốc), doc2 = tài liệu mới (bản sửa).

    Tuần 11: thêm tham số similarity_threshold (default 0.85, giảm từ 0.98).
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

            # Tuần 11: Dùng cả ratio VÀ character-level diff count
            # Ngay cả khi ratio cao (0.95+), nếu có thay đổi thực tế → MODIFIED
            if ratio >= similarity_threshold:
                # Double-check: đếm ký tự thay đổi thực sự
                changed_chars = _count_changed_chars(body1, body2)
                if changed_chars >= MIN_CHANGED_CHARS:
                    # Có thay đổi thực tế dù ratio cao → MODIFIED
                    inline = _compute_inline_diffs(body1, body2)
                    results.append(DiffItem(
                        heading=heading,
                        diff_type=DiffType.MODIFIED,
                        old_text=body1,
                        new_text=body2,
                        similarity=ratio,
                        inline_diffs=inline,
                    ))
                else:
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
