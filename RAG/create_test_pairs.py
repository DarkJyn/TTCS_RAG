#!/usr/bin/env python
"""
Script tạo tự động 5 cặp tài liệu test cho comparison evaluation.
Mỗi cặp: v1 = bản gốc, v2 = bản sửa đổi có kiểm soát.
Ground-truth được ghi vào eval_comparison_gt.jsonl.
"""

import json
import re
import shutil
from pathlib import Path

INPUT_DIR = Path("input_docs")
OUTPUT_DIR = Path("test_pairs")
GT_FILE = Path("eval_comparison_gt.jsonl")

# Regex nhận heading Điều
HEADING_RE = re.compile(
    r"^(Điều\s+\d+[a-z]?)\.\s*",
    re.IGNORECASE | re.MULTILINE,
)


def split_sections(text: str):
    """Tách văn bản thành danh sách (heading, content)."""
    sections = []
    positions = [(m.start(), m.group(1).strip() + ".") for m in HEADING_RE.finditer(text)]

    if not positions:
        return [("__preamble__", text)]

    # Phần trước Điều đầu tiên
    if positions[0][0] > 0:
        sections.append(("__preamble__", text[: positions[0][0]]))

    for i, (pos, heading) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        sections.append((heading, text[pos:end]))

    return sections


def rebuild_text(sections):
    """Ghép lại sections thành text."""
    return "".join(content for _, content in sections)


# ============================================================
# Định nghĩa 5 cặp tài liệu và các thay đổi
# ============================================================

PAIRS = [
    {
        "pair_id": "pair_01",
        "source": "Nghị định 160_2016_NĐ-CP điều kiện kinh doanh vận tải biển dịch vụ đại lý tàu biển lai dắt tàu biển mới nhất_1f8ab33d1b.txt",
        "modifications": {
            # MODIFIED: Sửa mức bảo lãnh trong Điều 5
            "Điều 5.": {
                "type": "modified",
                "find": "05 tỷ đồng Việt Nam",
                "replace": "10 tỷ đồng Việt Nam",
            },
            # MODIFIED: Sửa tỷ lệ vốn góp trong Điều 7
            "Điều 7.": {
                "type": "modified",
                "find": "49% vốn điều lệ",
                "replace": "51% vốn điều lệ",
            },
            # REMOVED: Xóa Điều 18 (điều khoản chuyển tiếp)
            "Điều 18.": {"type": "removed"},
            # ADDED: Thêm Điều 20 mới
            "__add__": {
                "type": "added",
                "heading": "Điều 20.",
                "content": "Điều 20. Quy định về giám sát hoạt động kinh doanh vận tải biển\n1. Cục Hàng hải Việt Nam thực hiện giám sát định kỳ hàng năm đối với các doanh nghiệp đã được cấp Giấy chứng nhận đủ điều kiện kinh doanh vận tải biển.\n2. Doanh nghiệp có trách nhiệm báo cáo tình hình hoạt động kinh doanh vận tải biển định kỳ 06 tháng một lần cho Cục Hàng hải Việt Nam.\n3. Trường hợp doanh nghiệp không thực hiện báo cáo theo quy định, Cục Hàng hải Việt Nam có quyền tạm đình chỉ Giấy chứng nhận đủ điều kiện kinh doanh vận tải biển.\n",
            },
        },
    },
    {
        "pair_id": "pair_02",
        "source": "Nghị định 62_2016_NĐ-CP điều kiện hoạt động giám định tư pháp xây dựng thí nghiệm chuyên ngành xây dựng mới nhất_59e7cfc1b6.txt",
        "modifications": {
            # MODIFIED: Sửa thời hạn hiệu lực trong Điều 5
            "Điều 5.": {
                "type": "modified",
                "find": "05\nnăm kể từ ngày cấp",
                "replace": "03\nnăm kể từ ngày cấp",
            },
            # MODIFIED: Sửa thời hạn trong Điều 6
            "Điều 6.": {
                "type": "modified",
                "find": "15 ngày làm",
                "replace": "10 ngày làm",
            },
            # REMOVED: Xóa Điều 8 (xử lý chuyển tiếp)
            "Điều 8.": {"type": "removed"},
        },
    },
    {
        "pair_id": "pair_03",
        "source": "Thông tư 01_2026_TT-NHNN cung cấp thông tin giữa Ngân hàng Nhà nước và Bảo hiểm tiền gửi mới nhất_876d0c207a.txt",
        "modifications": {
            # MODIFIED: Sửa thời hạn tra soát trong Điều 7
            "Điều 7.": {
                "type": "modified",
                "find": "15 ngày kể từ ngày nhận được đề nghị tra soát",
                "replace": "10 ngày làm việc kể từ ngày nhận được đề nghị tra soát",
            },
            # MODIFIED: Sửa thời hạn điều chỉnh trong Điều 7 (thêm)
            "Điều 3.": {
                "type": "modified",
                "find": "tính toàn vẹn, kịp thời",
                "replace": "tính chính xác, toàn vẹn, kịp thời",
            },
            # ADDED: Thêm Điều 16 mới
            "__add__": {
                "type": "added",
                "heading": "Điều 16.",
                "content": "Điều 16. Quy định về bảo mật thông tin điện tử\n1. Các thông tin trao đổi qua hệ thống điện tử phải được mã hóa theo tiêu chuẩn quốc gia về an toàn thông tin.\n2. Bảo hiểm tiền gửi Việt Nam và Ngân hàng Nhà nước phải thiết lập hệ thống xác thực hai yếu tố khi truy cập thông tin.\n3. Việc lưu trữ dữ liệu điện tử phải đảm bảo sao lưu dự phòng tối thiểu tại 02 địa điểm khác nhau.\n",
            },
        },
    },
    {
        "pair_id": "pair_04",
        "source": "Nghị định 76_2026_NĐ-CP sửa đổi Nghị định 125_2021_NĐ-CP xử phạt hành chính bình đẳng giới mới nhất_b212e68854.txt",
        "modifications": {
            # MODIFIED: Sửa mức phạt tiền trong Điều 2
            "Điều 2.": {
                "type": "modified",
                "find": "3.000.000 đồng đến 4.000.000 đồng",
                "replace": "5.000.000 đồng đến 7.000.000 đồng",
            },
            # MODIFIED: Sửa mức phạt trong Điều 5
            "Điều 5.": {
                "type": "modified",
                "find": "5.000.000 đồng đến 10.000.000 đồng",
                "replace": "7.000.000 đồng đến 12.000.000 đồng",
            },
            # REMOVED: Xóa Điều 13 (điều khoản chuyển tiếp)
            "Điều 13.": {"type": "removed"},
            # ADDED: Thêm Điều mới
            "__add__": {
                "type": "added",
                "heading": "Điều 16.",
                "content": "Điều 16. Quy định về tuyên truyền, phổ biến pháp luật\n1. Các cơ quan nhà nước có trách nhiệm tổ chức tuyên truyền, phổ biến nội dung Nghị định này đến người dân và cộng đồng.\n2. Kinh phí tuyên truyền được bố trí từ ngân sách nhà nước theo quy định hiện hành.\n",
            },
        },
    },
    {
        "pair_id": "pair_05",
        "source": "Nghị định 77_2026_NĐ-CP tổ chức hoạt động Quỹ Đổi mới công nghệ quốc gia mới nhất_b8d3f6f0cd.txt",
        "modifications": {
            # MODIFIED: Sửa mức tỷ lệ kinh phí trong Điều 11 (heading sẽ là "Điều\n11.")
            "Điều\n11.": {
                "type": "modified",
                "find": "05% đến 07%",
                "replace": "06% đến 08%",
            },
            # MODIFIED: Sửa số lần cấp kinh phí
            "Điều\n11._2": {
                "type": "modified",
                "source_heading": "Điều\n11.",
                "find": "không quá 03 lần",
                "replace": "không quá 04 lần",
            },
            # REMOVED: Xóa Điều 20 (điều khoản chuyển tiếp)
            "Điều\n20.": {"type": "removed"},
        },
    },
]


def apply_modifications(text: str, mods: dict, pair_id: str) -> tuple:
    """Áp dụng modifications lên text, trả về (modified_text, expected_diffs)."""
    sections = split_sections(text)
    expected_diffs = []

    new_sections = []
    for heading, content in sections:
        mod_key = heading
        if mod_key in mods:
            mod = mods[mod_key]
            if mod["type"] == "removed":
                expected_diffs.append({"heading": heading, "diff_type": "removed"})
                print(f"  [{pair_id}] REMOVED: {heading}")
                continue  # bỏ section này
            elif mod["type"] == "modified":
                find_str = mod["find"]
                replace_str = mod["replace"]
                if find_str in content:
                    content = content.replace(find_str, replace_str, 1)
                    expected_diffs.append({"heading": heading, "diff_type": "modified"})
                    print(f"  [{pair_id}] MODIFIED: {heading}")
                else:
                    print(f"  [{pair_id}] WARNING: Cannot find '{find_str[:40]}...' in {heading}")
        new_sections.append((heading, content))

    # Xử lý thêm heading trùng nhưng dùng key khác (e.g. "Điều\n11._2")
    for key, mod in mods.items():
        if key.endswith("_2") and mod["type"] == "modified":
            source_h = mod.get("source_heading", key[:-2])
            find_str = mod["find"]
            replace_str = mod["replace"]
            for i, (heading, content) in enumerate(new_sections):
                if heading == source_h and find_str in content:
                    new_sections[i] = (heading, content.replace(find_str, replace_str, 1))
                    # Không thêm diff mới vì cùng heading đã có
                    print(f"  [{pair_id}] MODIFIED (extra): {source_h}")
                    break

    # Thêm Điều mới
    if "__add__" in mods:
        add_mod = mods["__add__"]
        add_heading = add_mod["heading"]
        add_content = add_mod["content"]
        new_sections.append((add_heading, add_content))
        expected_diffs.append({"heading": add_heading, "diff_type": "added"})
        print(f"  [{pair_id}] ADDED: {add_heading}")

    modified_text = rebuild_text(new_sections)
    return modified_text, expected_diffs


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    all_gt = []

    for pair_cfg in PAIRS:
        pair_id = pair_cfg["pair_id"]
        source_file = INPUT_DIR / pair_cfg["source"]

        if not source_file.exists():
            print(f"SKIP {pair_id}: Source not found: {source_file.name[:60]}")
            continue

        print(f"\n=== {pair_id} ===")
        print(f"  Source: {source_file.name[:60]}...")

        # Đọc file gốc
        original_text = source_file.read_text(encoding="utf-8")

        # Copy v1
        v1_path = OUTPUT_DIR / f"{pair_id}_v1.txt"
        v1_path.write_text(original_text, encoding="utf-8")
        print(f"  Created: {v1_path.name}")

        # Tạo v2 với modifications
        modified_text, expected_diffs = apply_modifications(
            original_text, pair_cfg["modifications"], pair_id
        )

        v2_path = OUTPUT_DIR / f"{pair_id}_v2.txt"
        v2_path.write_text(modified_text, encoding="utf-8")
        print(f"  Created: {v2_path.name}")

        # Ground-truth entry
        gt_entry = {
            "pair_id": pair_id,
            "doc1": f"{pair_id}_v1.txt",
            "doc2": f"{pair_id}_v2.txt",
            "expected_diffs": expected_diffs,
        }
        all_gt.append(gt_entry)
        print(f"  Diffs: {len(expected_diffs)} changes")

    # Ghi ground-truth
    with GT_FILE.open("w", encoding="utf-8") as f:
        for entry in all_gt:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\n=== DONE ===")
    print(f"Created {len(all_gt)} pairs in {OUTPUT_DIR}/")
    print(f"Ground-truth written to {GT_FILE}")
    print(f"\nTotal expected diffs:")
    for entry in all_gt:
        diffs_summary = ", ".join(
            f"{d['heading']}({d['diff_type']})" for d in entry["expected_diffs"]
        )
        print(f"  {entry['pair_id']}: {diffs_summary}")


if __name__ == "__main__":
    main()
