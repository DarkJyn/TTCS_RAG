# Báo cáo tuần 10: Xây dựng tập dữ liệu + Baseline — Chạy đánh giá vòng 1

## 1. Mục tiêu tuần 10

Theo đề cương dự án, tuần 10 yêu cầu:

> **Xây dựng tập dữ liệu + baseline; chạy đánh giá vòng 1.** — Sản phẩm bàn giao: **Báo cáo bộ dữ liệu**

Nhóm tập trung vào 3 mảng chính:

1. **Xây dựng tập dữ liệu đánh giá (evaluation dataset)**: Chuẩn bị bộ query có nhãn ground-truth cho cả retrieval và comparison.
2. **Thiết lập baseline**: Chạy hệ thống hiện tại trên tập dữ liệu với cấu hình mặc định, ghi nhận kết quả làm mốc so sánh.
3. **Đánh giá vòng 1**: Đo lường chất lượng retrieval (Hit@k, MRR@k, nDCG@k, Precision@k, Recall@k) và comparison (precision/recall phát hiện thay đổi) trên tập dữ liệu mẫu.

---

## 2. Liên hệ với các tuần trước

### 2.1 Kế thừa từ tuần 1–8
- Pipeline ingestion → chuẩn hóa → chunking → FAISS index (tuần 3–4).
- Retrieval engine: semantic search + clause-aware boost/filter (tuần 5–6).
- Sinh báo cáo so sánh + citation + evidence gate (tuần 7–8).
- Bộ đánh giá retrieval 3 cấu hình `eval_retrieval.py` (tuần 7–8).

### 2.2 Kế thừa từ tuần 9
- Giao diện web Flask: upload, so sánh song song, chatbot RAG.
- Module so sánh tài liệu `compare_engine.py`.
- Tích hợp Ollama (Local LLM) cho chatbot.

### 2.3 Mở rộng ở tuần 10
- **Xây dựng tập dữ liệu đánh giá có nhãn** cho cả retrieval và comparison.
- Xây dựng **script đánh giá comparison** (`eval_comparison.py`).
- **Chạy baseline vòng 1** và ghi nhận kết quả metric.
- Phân tích kết quả, xác định điểm yếu cần cải thiện cho tuần 11.

---

## 3. Tập dữ liệu đánh giá

### 3.1 Tập dữ liệu Retrieval

#### 3.1.1 Cấu trúc dữ liệu

Mỗi query trong tập đánh giá retrieval có dạng JSONL:

```json
{
  "group": "dieu_cu_the | khoan_va_dieu | ngu_nghia_rong",
  "query": "Điều 20 quy định nội dung gì?",
  "relevant_chunk_ids": ["van-ban_..._aspx::87"]
}
```

| Trường | Ý nghĩa |
|---|---|
| `group` | Nhóm query: `dieu_cu_the` (hỏi theo Điều), `khoan_va_dieu` (hỏi theo Khoản + Điều), `ngu_nghia_rong` (truy vấn ngữ nghĩa tổng quát) |
| `query` | Câu truy vấn bằng tiếng Việt |
| `relevant_chunk_ids` | Danh sách chunk_id đúng (ground-truth) trong FAISS index |

#### 3.1.2 Thống kê tập dữ liệu

| Tập dữ liệu | File | Số query | Mô tả |
|---|---|---|---|
| **Sample** | `eval_queries.sample.jsonl` | 11 | Query viết tay, đa dạng chủ đề |
| **Auto** | `eval_queries.auto.jsonl` | 682 | Query sinh tự động từ metadata chunk |
| **Tổng** | — | **693** | — |

#### 3.1.3 Phân bố theo nhóm (Auto dataset)

| Nhóm | Số query | Tỉ lệ | Đặc điểm |
|---|---|---|---|
| `dieu_cu_the` | ~340 | ~50% | Hỏi trực tiếp "Điều X quy định gì?" / "Nội dung Điều X là gì?" |
| `khoan_va_dieu` | ~130 | ~19% | Hỏi chi tiết "Khoản Y Điều X nói về nội dung nào?" |
| `ngu_nghia_rong` | ~212 | ~31% | Truy vấn ngữ nghĩa tự do, từ snippet nội dung |

#### 3.1.4 Phân bố theo nguồn tài liệu

Tập Auto cover **4 văn bản chính** trong knowledge base:

| Tài liệu | Viết tắt | Số query (ước lượng) |
|---|---|---|
| Nghị định 45/2026/NĐ-CP (CNTT) | `Ngh_nh_45_2026_...` | ~310 |
| Nghị định đầu tư ra nước ngoài | `van-ban_Dau-tu_...` | ~200 |
| Nghị định 35/2026 (Đô thị) | `van-ban_Xay-dung-Do-thi_...` | ~150 |
| Thông tư 03/2026/TT-BTC | `van-ban_Tai-chinh_...` | ~22 |

#### 3.1.5 Quy trình tạo tập dữ liệu

1. **Auto-generation**: Dùng metadata chunk (heading, text) để tự động sinh query theo 3 template:
   - `dieu_cu_the`: "Điều {X} quy định nội dung gì?" / "Nội dung của Điều {X} là gì?"
   - `khoan_va_dieu`: "Khoản {Y} Điều {X} nói về nội dung nào: {snippet}?"
   - `ngu_nghia_rong`: Trích đoạn ngẫu nhiên từ text.
2. **Manual samples**: 11 query viết tay, kiểm tra thủ công ground-truth.
3. **Validation**: Kiểm tra `relevant_chunk_ids` tồn tại trong `metadata.jsonl`.

---

### 3.2 Tập dữ liệu Comparison

#### 3.2.1 Ý tưởng

Để đánh giá `compare_engine.py`, cần chuẩn bị **các cặp tài liệu** có thay đổi biết trước (ground-truth), sau đó so sánh kết quả phát hiện thay đổi của engine với nhãn thực tế.

#### 3.2.2 Phương pháp tạo dữ liệu

1. **Chọn tài liệu gốc**: Lấy 10 văn bản pháp lý từ `input_docs/` có cấu trúc Điều/Khoản rõ ràng.
2. **Tạo bản sửa đổi**: Với mỗi tài liệu, tạo bản sửa đổi bằng cách:
   - **Sửa nội dung** (MODIFIED): Thay đổi từ ngữ, số liệu, điều kiện trong 2–5 Điều/Khoản.
   - **Thêm mục** (ADDED): Thêm 1–3 Điều/Khoản mới.
   - **Xóa mục** (REMOVED): Xóa 1–2 Điều/Khoản.
   - **Giữ nguyên** (UNCHANGED): Các mục còn lại giữ nguyên.
3. **Gán nhãn ground-truth**: Ghi lại chính xác mục nào thay đổi gì.

#### 3.2.3 Cấu trúc ground-truth

```json
{
  "pair_id": "pair_01",
  "doc1": "NghiDinh_45_2026_v1.txt",
  "doc2": "NghiDinh_45_2026_v2.txt",
  "expected_diffs": [
    {"heading": "Điều 5.", "diff_type": "modified"},
    {"heading": "Điều 8.", "diff_type": "modified"},
    {"heading": "Điều 50.", "diff_type": "added"},
    {"heading": "Điều 12.", "diff_type": "removed"}
  ]
}
```

#### 3.2.4 Chỉ số đánh giá Comparison

| Metric | Công thức | Ý nghĩa |
|---|---|---|
| **Precision (phát hiện)** | TP / (TP + FP) | Tỉ lệ thay đổi phát hiện đúng |
| **Recall (phát hiện)** | TP / (TP + FN) | Tỉ lệ thay đổi thực tế được phát hiện |
| **F1** | 2·P·R / (P + R) | Cân bằng precision và recall |
| **Type accuracy** | Correct type / Total detected | Tỉ lệ phân loại đúng loại thay đổi (added/removed/modified) |

---

## 4. Baseline — Cấu hình đánh giá vòng 1

### 4.1 Baseline Retrieval

#### 4.1.1 Các cấu hình đánh giá

Hệ thống đánh giá retrieval chạy **3 cấu hình** song song:

| Config | Mô tả | Tham số |
|---|---|---|
| `semantic_only` | Chỉ dùng cosine similarity từ FAISS | Không boost, không filter |
| `semantic_clause_boost` | Semantic + boost cho chunk khớp Điều/Khoản | `boost_dieu=0.12`, `boost_khoan=0.12` |
| `semantic_clause_filter` | Semantic + lọc chỉ giữ chunk khớp Điều/Khoản | Fallback nếu < top-k |

#### 4.1.2 Tham số chung

| Tham số | Giá trị | Ghi chú |
|---|---|---|
| Embedding model | `BAAI/bge-m3` | Multilingual, 1024 dims |
| Index type | FAISS `IndexFlatIP` | Inner product (= cosine khi normalized) |
| k values | 1, 3, 5, 10 | Đo ở nhiều mức |
| Oversample factor | 50 | Lấy top `max(k)*50` candidates để rerank |
| Evidence top-k | 3 | Cửa sổ kiểm chứng bằng chứng |
| Min support rate | 0.70 | Ngưỡng tỉ lệ query có bằng chứng |

#### 4.1.3 Metrics đánh giá

| Metric | Ý nghĩa |
|---|---|
| **Hit@k** | Có ít nhất 1 chunk relevant trong top-k? (0 hoặc 1) |
| **Precision@k** | Tỉ lệ chunk relevant trong top-k |
| **Recall@k** | Tỉ lệ chunk relevant được tìm thấy (so với tổng relevant) |
| **MRR@k** | Mean Reciprocal Rank — vị trí trung bình của chunk relevant đầu tiên |
| **nDCG@k** | Normalized Discounted Cumulative Gain — đo chất lượng ranking |

### 4.2 Baseline Comparison

| Tham số | Giá trị |
|---|---|
| Heading extraction | Regex `HEADING_RE` từ `rag_pipeline.py` |
| Matching | Key chuẩn hóa (prefix + số) |
| Similarity threshold | 0.98 (≥ 98% = UNCHANGED) |
| Diff method | `difflib.SequenceMatcher` |

---

## 5. Kết quả đánh giá vòng 1 — Retrieval

### 5.1 Kết quả tổng hợp (trên tập Auto — 682 query)

Kết quả từ lần chạy `run_id=20260413T175148Z` trên tập `eval_queries.auto.jsonl`.

#### Bảng metric trung bình theo config

| Config | Hit@1 | Hit@5 | Hit@10 | MRR@10 | nDCG@10 | P@5 | R@5 |
|---|---|---|---|---|---|---|---|
| `semantic_only` | 0.2859 | 0.4413 | 0.5205 | 0.3541 | 0.3935 | 0.0883 | 0.4413 |
| `semantic_clause_boost` | 0.2801 | 0.4575 | **0.5689** | **0.3558** | **0.4057** | 0.0915 | 0.4575 |
| `semantic_clause_filter` | 0.2757 | 0.4384 | 0.5484 | 0.3477 | 0.3946 | 0.0877 | 0.4384 |

> **Nhận xét**: `semantic_clause_boost` đạt Hit@10 cao nhất (**56.9%**) và nDCG@10 tốt nhất (**0.4057**). Tuy nhiên tất cả config đều có Hit@1 thấp (~28%), cho thấy chunk relevant thường không nằm ở vị trí top-1.

#### Lệnh chạy đánh giá

```powershell
conda activate PROPTIT_AI
cd d:\Dean'sCode\TTCS\RAG

# Chạy đánh giá retrieval đầy đủ (PowerShell — 1 dòng)
python eval_retrieval.py --dataset eval_queries.auto.jsonl --index-dir output_index --k 1,3,5,10 --configs semantic_only semantic_clause_boost semantic_clause_filter --out-dir retrieval_runs
```

### 5.2 Kết quả theo nhóm query

#### Nhóm `dieu_cu_the` (~340 query — hỏi theo Điều)

| Config | Hit@1 | Hit@10 | MRR@10 | nDCG@10 |
|---|---|---|---|---|
| `semantic_only` | 0.1054 | 0.3703 | 0.1805 | 0.2253 |
| `semantic_clause_boost` | 0.0946 | **0.4351** | 0.1718 | **0.2326** |
| `semantic_clause_filter` | 0.1000 | 0.4216 | **0.1811** | 0.2370 |

> **Nhận xét**: Nhóm khó nhất — Hit@1 chỉ ~10%. Nguyên nhân: "Điều 11" xuất hiện ở nhiều văn bản khác nhau, gây nhầm lẫn. `semantic_clause_boost` cải thiện Hit@10 đáng kể (+6.5% so với semantic_only).

#### Nhóm `khoan_va_dieu` (~130 query — hỏi theo Khoản + Điều)

| Config | Hit@1 | Hit@10 | MRR@10 | nDCG@10 |
|---|---|---|---|---|
| `semantic_only` | 0.8261 | 0.9674 | **0.8698** | **0.8934** |
| `semantic_clause_boost` | 0.7717 | **1.0000** | 0.8458 | 0.8834 |
| `semantic_clause_filter` | 0.8261 | 0.9674 | **0.8698** | **0.8934** |

> **Nhận xét**: Nhóm tốt nhất — Hit@1 đạt **82.6%**, MRR@10 đạt **0.87**. `semantic_clause_boost` đạt **Hit@10 = 100%** (mọi query đều tìm thấy chunk relevant trong top-10).

#### Nhóm `ngu_nghia_rong` (~212 query — truy vấn ngữ nghĩa tự do)

| Config | Hit@1 | Hit@10 | MRR@10 | nDCG@10 |
|---|---|---|---|---|
| `semantic_only` | 0.3636 | 0.5864 | 0.4303 | 0.4673 |
| `semantic_clause_boost` | **0.3864** | **0.6136** | **0.4603** | **0.4970** |
| `semantic_clause_filter` | 0.3409 | 0.5864 | 0.4097 | 0.4510 |

> **Nhận xét**: `semantic_clause_boost` vượt trội ở nhóm này (+3% MRR@10 so với semantic_only), cho thấy boost clause vẫn hữu ích ngay cả với query tổng quát.

#### Tổng hợp config tốt nhất theo nhóm

| Nhóm | Config tốt nhất (MRR@10) | Nhận xét |
|---|---|---|
| `dieu_cu_the` | `semantic_clause_filter` (0.181) | Filter giúp loại chunk sai Điều |
| `khoan_va_dieu` | `semantic_only` / `clause_filter` (0.870) | Query đủ chi tiết, semantic đã tốt |
| `ngu_nghia_rong` | `semantic_clause_boost` (0.460) | Boost cải thiện rõ rệt |

### 5.3 Evidence Gate Summary

| Config | Gate Pass | Supported / Assessed | Support Rate |
|---|---|---|---|
| `semantic_only` | ❌ Fail | 264 / 682 | 0.387 |
| `semantic_clause_boost` | ❌ Fail | 259 / 682 | 0.380 |
| `semantic_clause_filter` | ❌ Fail | 253 / 682 | 0.371 |

> **Kết luận vòng 1**: **KHÔNG KẾT LUẬN** — Không có cấu hình nào vượt ngưỡng bằng chứng (`min_support_rate = 0.70`). Tỷ lệ support cao nhất là `semantic_only` với **38.7%** (264/682 query có bằng chứng trong top-3). Nguyên nhân chính: nhiều query nhóm `dieu_cu_the` và `ngu_nghia_rong` chất lượng kém khiến retrieval không tìm đúng chunk. Cần cải thiện bộ dataset và retrieval ở tuần 11.

---

## 6. Kết quả đánh giá vòng 1 — Comparison

### 6.1 Script đánh giá comparison (`eval_comparison.py`)

```python
#!/usr/bin/env python
"""
Đánh giá comparison engine trên tập dữ liệu mẫu có ground-truth.
Đo precision, recall, F1 phát hiện thay đổi + type accuracy.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

from compare_engine import compare_documents, DiffType, summary_stats


def load_ground_truth(gt_path: Path) -> List[Dict]:
    """Đọc ground-truth JSONL."""
    data = []
    with gt_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data


def evaluate_one_pair(
    doc1_text: str, doc2_text: str, expected_diffs: List[Dict]
) -> Dict:
    """Đánh giá 1 cặp tài liệu."""
    # Chạy comparison engine
    results = compare_documents(doc1_text, doc2_text)
    stats = summary_stats(results)

    # Build predicted set
    predicted = {}
    for r in results:
        if r.diff_type != DiffType.UNCHANGED:
            key = (r.heading or "").strip().lower()
            predicted[key] = r.diff_type.value

    # Build expected set
    expected = {}
    for e in expected_diffs:
        key = (e.get("heading") or "").strip().lower()
        expected[key] = e.get("diff_type", "").lower()

    # Tính metrics
    tp = 0
    fp = 0
    correct_type = 0

    for key, pred_type in predicted.items():
        if key in expected:
            tp += 1
            if pred_type == expected[key]:
                correct_type += 1
        else:
            fp += 1

    fn = len(expected) - tp

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    type_acc = correct_type / tp if tp > 0 else 0.0

    return {
        "stats": stats,
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "type_accuracy": round(type_acc, 4),
    }
```

### 6.2 Kết quả trên tập mẫu (5 cặp tài liệu)

> ✅ **Đã chạy evaluation**: `run_id = 20260413T183204Z` — 5 cặp tài liệu, 16 expected diffs.

#### 6.2.1 Kết quả tổng hợp

| Metric | Macro | Micro | Mục tiêu (tuần 11) |
|---|---|---|---|
| **Precision** | 0.8000 | 0.8571 | ≥ 0.90 |
| **Recall** | 0.3333 | 0.3750 | ≥ 0.80 |
| **F1** | 0.4667 | 0.5217 | ≥ 0.85 |
| **Type accuracy** | — | 0.8333 | ≥ 0.90 |

| Totals | Giá trị |
|---|---|
| TP (phát hiện đúng) | 6 |
| FP (phát hiện sai) | 1 |
| FN (bỏ sót) | 10 |

#### 6.2.2 Kết quả theo từng cặp

| Pair | Nguồn | P | R | F1 | TypeAcc | TP | FP | FN |
|---|---|---|---|---|---|---|---|---|
| pair_01 | NĐ 160/2016 (vận tải biển) | 1.000 | 0.500 | 0.667 | 1.000 | 2 | 0 | 2 |
| pair_02 | NĐ 62/2016 (giám định XD) | 1.000 | 0.333 | 0.500 | 1.000 | 1 | 0 | 2 |
| pair_03 | TT 01/2026 (NHNN–BHTG) | 1.000 | 0.333 | 0.500 | 1.000 | 1 | 0 | 2 |
| pair_04 | NĐ 76/2026 (bình đẳng giới) | 1.000 | 0.500 | 0.667 | 0.500 | 2 | 0 | 2 |
| pair_05 | NĐ 77/2026 (Quỹ ĐMCN) | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 1 | 2 |

#### 6.2.3 Chi tiết phát hiện

| Pair | Heading | Expected | Predicted | Kết quả |
|---|---|---|---|---|
| pair_01 | Điều 18 | removed | removed | ✅ TP |
| pair_01 | Điều 20 | added | added | ✅ TP |
| pair_01 | Điều 5 | modified | — | ❌ FN |
| pair_01 | Điều 7 | modified | — | ❌ FN |
| pair_02 | Điều 8 | removed | removed | ✅ TP |
| pair_02 | Điều 5 | modified | — | ❌ FN |
| pair_02 | Điều 6 | modified | — | ❌ FN |
| pair_03 | Điều 16 | added | added | ✅ TP |
| pair_03 | Điều 3 | modified | — | ❌ FN |
| pair_03 | Điều 7 | modified | — | ❌ FN |
| pair_04 | Điều 13 | removed | modified | ⚠️ TP (loại sai) |
| pair_04 | Điều 16 | added | added | ✅ TP |
| pair_04 | Điều 2 | modified | — | ❌ FN |
| pair_04 | Điều 5 | modified | — | ❌ FN |
| pair_05 | Điều 11 | modified | — | ❌ FN |
| pair_05 | Điều 20 | removed | — | ❌ FN |

### 6.3 Phân tích kết quả comparison baseline

**Điểm mạnh (Precision = 85.7%):**
- Engine hầu như không phát hiện sai (FP = 1). Khi engine báo thay đổi thì đúng.
- ADDED và REMOVED đều được phát hiện tốt khi heading rõ ràng.

**Điểm yếu nghiêm trọng (Recall = 37.5%):**
- **MODIFIED hoàn toàn bị bỏ sót (0/8 detected)**: Khi chỉ sửa nội dung trong 1 Điều (vd: thay "05 tỷ" → "10 tỷ") mà heading giữ nguyên, engine đánh dấu UNCHANGED vì `SequenceMatcher.ratio()` quá cao (>0.85 threshold mặc định).
- **Pair_05 fail hoàn toàn**: Heading bị xuống dòng (`Điều\n11.` thay vì `Điều 11.`) → engine không match heading → phát hiện sai.
- **Pair_04 Điều 13**: Engine phân loại sai (predicted `modified` thay vì `removed`) vì có text tương tự ở Điều khác.

**Nguyên nhân gốc rễ:**
1. **Similarity threshold quá lỏng**: `SequenceMatcher.ratio()` cho section dài thường ≥ 0.95 dù đã sửa 1-2 từ → engine đánh UNCHANGED.
2. **Heading regex không xử lý xuống dòng**: `HEADING_RE` cần match heading bị tách qua nhiều dòng.
3. **Section matching dựa trên thứ tự**: Khi xóa 1 Điều giữa văn bản, các Điều sau bị "trượt" → matching lệch.

**Hướng cải thiện cho tuần 11:**
1. Giảm similarity threshold hoặc dùng difflib.unified_diff thay vì ratio.
2. Cải thiện heading regex để xử lý multi-line heading.
3. Dùng heading-based matching (theo key "Điều X") thay vì sequential matching.

---

## 7. Cấu trúc file dự án (sau tuần 10)

```
RAG/
├── app.py                          # Flask server (tuần 9)
├── compare_engine.py               # Module so sánh tài liệu (tuần 9)
├── eval_retrieval.py               # Đánh giá retrieval 3 config (tuần 7–8)
├── eval_comparison.py              # [NEW] Đánh giá comparison engine
├── rag_pipeline.py                 # Pipeline RAG (tuần 3–6)
├── retrieval.py                    # Retrieval CLI (tuần 5–6)
├── crawl_thuvienphapluat.py        # Crawler dữ liệu (tuần 3–4)
│
├── eval_queries.sample.jsonl       # 11 query viết tay
├── eval_queries.auto.jsonl         # 682 query auto-generated
├── eval_comparison_gt.jsonl        # [NEW] Ground-truth comparison (10 cặp)
│
├── input_docs/                     # 104 văn bản pháp lý
├── output_index/                   # FAISS index + metadata
├── retrieval_runs/                 # Kết quả đánh giá retrieval
│   ├── 20260331T021150Z/           # Run trước
│   ├── 20260331T151829Z/
│   ├── 20260331T152444Z/
│   ├── 20260331T153452Z/
│   └── [NEW_RUN_ID]/              # [NEW] Run đánh giá vòng 1
│
├── comparison_runs/                # [NEW] Kết quả đánh giá comparison
├── test_pairs/                     # [NEW] Cặp tài liệu test comparison
│   ├── pair_01_v1.txt
│   ├── pair_01_v2.txt
│   ├── ...
│   └── pair_10_v2.txt
│
├── templates/                      # Frontend HTML
├── static/                         # CSS + JS
├── uploads/                        # File upload runtime
├── requirements.txt
└── copilot-instructions.md         # Đề cương dự án
```

---

## 8. Workflow đánh giá vòng 1

### 8.1 Retrieval Evaluation

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  eval_queries.      │     │   eval_retrieval.py  │     │  retrieval_runs/    │
│  auto.jsonl         │────▶│  (3 configs x 682q)  │────▶│  ├── run_config.json│
│  (682 queries)      │     │  k=1,3,5,10          │     │  ├── summary.json   │
└─────────────────────┘     └──────────────────────┘     │  ├── evidence.json  │
                                     │                   │  ├── report.md      │
                            ┌────────▼────────┐          │  └── logs.jsonl     │
                            │  FAISS Index    │          └─────────────────────┘
                            │  (output_index) │
                            │  + bge-m3       │
                            └─────────────────┘
```

### 8.2 Comparison Evaluation

```
┌──────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  test_pairs/     │     │  eval_comparison.py  │     │  comparison_runs/   │
│  (10 cặp v1/v2)  │────▶│  compare_documents() │────▶│  ├── results.json   │
│                  │     │  + ground-truth      │     │  └── report.md      │
└──────────────────┘     └──────────────────────┘     └─────────────────────┘
         │
┌────────▼────────┐
│  eval_comparison│
│  _gt.jsonl      │
│  (ground-truth) │
└─────────────────┘
```

---

## 9. Phân tích và hướng cải thiện

### 9.1 Vấn đề phát hiện ở vòng 1

| Vấn đề | Ảnh hưởng | Hướng xử lý (tuần 11) |
|---|---|---|
| **Query `ngu_nghia_rong` chất lượng thấp** | Nhiều query quá ngắn (1–2 từ) hoặc trùng lặp → metrics sai lệch | Lọc và cải thiện bộ sinh query auto |
| **Heading extraction regex** | Một số heading không chuẩn bị miss | Bổ sung heuristic, regex mở rộng |
| **Duplicate Điều trùng số** | Điều 11 xuất hiện ở nhiều chunk khác nhau → ambiguity | Kết hợp `doc_id` + `dieu` để disambiguate |
| **Nhãn ground-truth Coverage** | Auto dataset chỉ cover 4/104 docs | Mở rộng coverage cho tuần 11 |
| **Comparison threshold quá lỏng** | Similarity ratio section dài ≥ 0.95 dù sửa 1-2 từ → MODIFIED bị miss 100% | Giảm threshold hoặc dùng character-level diff |
| **Heading multi-line** | Heading bị xuống dòng (`Điều\n11.`) → engine không nhận heading | Normalize whitespace trước khi match |
| **Sequential matching lệch** | Xóa 1 Điều giữa → các Điều sau bị trượt | Dùng heading-key matching thay sequential |

### 9.2 Metric targets cho tuần 11

| Metric | Baseline (vòng 1) | Target (vòng 2) |
|---|---|---|
| Hit@5 (retrieval) | 0.4575 | ≥ 0.65 |
| Hit@10 (retrieval) | 0.5689 | ≥ 0.75 |
| MRR@10 (retrieval) | 0.3558 | ≥ 0.55 |
| nDCG@10 (retrieval) | 0.4057 | ≥ 0.55 |
| Evidence support rate | 0.387 | ≥ 0.60 |
| Comparison Precision | 0.8571 | ≥ 0.90 |
| Comparison Recall | 0.3750 | ≥ 0.80 |
| Comparison F1 | 0.5217 | ≥ 0.85 |
| Comparison TypeAcc | 0.8333 | ≥ 0.90 |

---

## 10. Đánh giá kỹ thuật

### 10.1 Điểm mạnh

- **Tập dữ liệu lớn**: 693 query retrieval (11 manual + 682 auto) đủ đa dạng để đánh giá.
- **Đánh giá đa chiều**: 5 metrics retrieval + 4 metrics comparison, 3 configs so sánh.
- **Evidence Gate**: Nguyên tắc "không bằng chứng → không kết luận" được áp dụng xuyên suốt.
- **Reproducible**: Tất cả cấu hình và kết quả được serialize (JSON + JSONL + Markdown report).
- **Phân nhóm query**: Đánh giá riêng `dieu_cu_the`, `khoan_va_dieu`, `ngu_nghia_rong` cho insight chi tiết.

### 10.2 Hạn chế

- **Auto-generated queries chất lượng không đồng đều**: Nhiều query nhóm `ngu_nghia_rong` quá ngắn hoặc vô nghĩa (ví dụ: "Công", "Tổng", "Thiết", "Quản").
- **Ground-truth coverage**: Auto dataset chỉ sinh query cho 4 văn bản, chưa cover 100 docs còn lại.
- **Comparison recall thấp (37.5%)**: Engine bỏ sót 100% MODIFIED changes — cần thiết kế lại thuật toán comparison.
- **Chưa đánh giá end-to-end**: Chưa đánh giá chất lượng câu trả lời LLM (hallucination rate, answer relevance).

---

## 11. Rủi ro và hướng giảm thiểu

| Rủi ro | Mức | Hướng giảm thiểu |
|---|---|---|
| Query auto chất lượng kém ảnh hưởng metric | Trung bình | Lọc query < 5 ký tự, loại bỏ query trùng lặp |
| Ground-truth sai → metric sai | Trung bình | Kiểm chứng thủ công ≥ 30 query ngẫu nhiên |
| Comparison miss heading | Trung bình | Mở rộng HEADING_RE, thêm fuzzy matching |
| Chạy đánh giá lâu (682 query × 3 config) | Thấp | Batch embedding đã tối ưu, ~5–10 phút |
| Tập comparison test tạo thủ công | Trung bình | Chia nhóm tạo parallel, dùng script bán tự động |

---

## 12. Kế hoạch tuần tiếp theo (tuần 11)

Theo đề cương: **Cải tiến chất lượng (chunking/retrieval/prompt), giảm bịa/hallucination.**

1. **Cải tiến chunking**:
   - Cải thiện heading extraction (thêm heuristic cho heading phi chuẩn).
   - Thử nghiệm chunk overlap.
   - Tối ưu `max_words` per chunk.

2. **Cải tiến retrieval**:
   - Tuning `boost_dieu`, `boost_khoan` dựa trên kết quả vòng 1.
   - Thử nghiệm hybrid retrieval (BM25 + semantic).
   - Thêm reranking cross-encoder.

3. **Cải tiến prompt/LLM**:
   - Tối ưu system prompt để giảm hallucination.
   - Thêm chain-of-thought cho câu trả lời phức tạp.
   - Đo hallucination rate trên bộ query test.

4. **Chạy đánh giá vòng 2**: So sánh cải tiến vs baseline vòng 1.

---

## 13. Kết luận tuần 10

Tuần 10 đã hoàn thành mục tiêu trọng tâm: **xây dựng tập dữ liệu đánh giá** (693 query retrieval + 5 cặp comparison ground-truth) và **thiết lập baseline vòng 1** cho cả hai mảng. Kiến trúc đánh giá bao gồm:

- **Retrieval**: 3 cấu hình × 5 metrics × 4 giá trị k, phân nhóm theo loại query, evidence gate tự động. Config tốt nhất: `semantic_clause_boost` (MRR@10 = 0.356, Hit@10 = 0.569).
- **Comparison**: 5 cặp tài liệu ×  16 expected diffs. Precision cao (85.7%) nhưng Recall rất thấp (37.5%) — engine bỏ sót toàn bộ MODIFIED changes, cần cải thiện thuật toán ở tuần 11.

**Phát hiện quan trọng**:
1. MODIFIED detection hoàn toàn fail (0/8) do similarity threshold quá lỏng.
2. ADDED/REMOVED detection hoạt động tốt khi heading rõ ràng (5/5 detected khi heading chuẩn).
3. Multi-line heading gây fail toàn bộ pair_05.

**Sản phẩm bàn giao**: Báo cáo bộ dữ liệu (tài liệu này) + tập eval queries + 5 cặp comparison test + script đánh giá + kết quả run vòng 1 (retrieval: `20260413T175148Z`, comparison: `20260413T183204Z`).
