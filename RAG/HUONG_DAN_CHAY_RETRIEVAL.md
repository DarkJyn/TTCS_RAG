## Hướng dẫn chạy so sánh Retrieval (RAG)

Tài liệu này hướng dẫn bạn chạy **so sánh retrieval** theo đúng yêu cầu 1–3:

- Chọn cấu hình so sánh (Baseline / Config A / Config B)
- Chuẩn bị bộ truy vấn đánh giá (JSONL, có nhóm + `relevant_chunk_ids`)
- Chạy retrieval cho từng cấu hình và **lưu top‑k** với đủ trường:
  `rank, score, chunk_id, heading, source_path, snippet`

Repo hiện đã có sẵn các script chính:
- `RAG/rag_pipeline.py`: build index FAISS + metadata
- `RAG/eval_retrieval.py`: chạy retrieval theo nhiều cấu hình và xuất log
- `RAG/generate_eval_queries.py`: tự sinh dataset query (có nhãn) từ `metadata.jsonl`

---

## 1) Điều kiện tiên quyết

### 1.1 Cài dependencies

Bạn nên dùng virtualenv:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r RAG/requirements.txt
```

Ghi chú:
- Nếu bạn xử lý `.doc` thì `rag_pipeline.py` có thể cần `textract` (đã có trong `requirements.txt`).
- Khi chạy lần đầu, `sentence-transformers` có thể tải model từ HuggingFace → có thể thấy warning về `HF_TOKEN` (không bắt buộc).

---

## 2) Chuẩn bị “nguồn dữ liệu để trích dẫn” (Index + Metadata)

Retrieval chạy trên **FAISS index** và **metadata.jsonl**.

Trong repo bạn đang dùng:
- `RAG/output_index/index.faiss`
- `RAG/output_index/metadata.jsonl`
- `RAG/output_index/manifest.json`

Nếu bạn chưa có index hoặc muốn build lại:

```bash
python RAG/rag_pipeline.py index --input-dir RAG/input_docs --output-dir RAG/output_index
```

---

## 3) Yêu cầu 1 — Chọn cấu hình cần so sánh

Trong `RAG/eval_retrieval.py` có 3 cấu hình:

- **Baseline**: `semantic_only`
- **Config A**: `semantic_clause_boost`
- **Config B**: `semantic_clause_filter`

Bạn có thể chọn config muốn chạy bằng `--configs`:

```bash
python RAG/eval_retrieval.py ... --configs semantic_only semantic_clause_boost semantic_clause_filter
```

### 3.1 Khác nhau giữa 3 config

- **`semantic_only`**
  - Chỉ dùng semantic search (FAISS + embedding).
  - Score chính là `base_score` từ FAISS.

- **`semantic_clause_boost`**
  - Nếu query có “Điều X” và/hoặc “Khoản Y”, script sẽ kiểm tra chunk có match Điều/Khoản không.
  - Nếu match thì **cộng điểm** (`--boost-dieu`, `--boost-khoan`) vào score.

- **`semantic_clause_filter`**
  - Nếu query có “Điều X” và/hoặc “Khoản Y”, script sẽ **lọc bỏ** các chunk không match.
  - Nếu bạn **không bật** `--strict-filter` và lọc xong chưa đủ top‑k, script sẽ “đệm” thêm kết quả semantic khác để đủ top‑k (nhưng các kết quả đệm không đảm bảo match clause).

---

## 4) Yêu cầu 2 — Chuẩn bị bộ truy vấn đánh giá (dataset JSONL)

Dataset là file `.jsonl`, mỗi dòng là 1 object JSON.

### 4.1 Schema mỗi dòng

- **`query`** (bắt buộc): câu hỏi
- **`relevant_chunk_ids`** (bắt buộc): list `chunk_id` bạn kỳ vọng là đúng (ground-truth)
- **`group`** (không bắt buộc): nhóm truy vấn, ví dụ:
  - `dieu_cu_the`
  - `khoan_va_dieu`
  - `ngu_nghia_rong`

Ví dụ:

```json
{"group":"khoan_va_dieu","query":"Khoản 1 Điều 8 quy định gì?","relevant_chunk_ids":["DOC::16"]}
```

### 4.2 Các dataset mẫu có sẵn trong repo

- `RAG/eval_queries.sample.jsonl`: dataset nhỏ (không có `group`)
- `RAG/eval_queries.template.jsonl`: dataset nhỏ có `group`
- `RAG/eval_queries.auto.jsonl`: dataset lớn hơn (tự sinh)

### 4.3 Tự sinh dataset lớn hơn (khuyến nghị)

Script `RAG/generate_eval_queries.py` sẽ tự sinh query từ `RAG/output_index/metadata.jsonl`
và gán nhãn `relevant_chunk_ids` theo đúng `chunk_id` đã dùng để tạo query.

```bash
python RAG/generate_eval_queries.py --index-dir RAG/output_index --out RAG/eval_queries.auto.jsonl --max-chunks 220
```

Tham số hữu ích:
- `--max-chunks`: lấy tối đa bao nhiêu chunk để sinh query
- `--per-dieu`, `--per-khoan`, `--per-semantic`: số query sinh ra theo từng nhóm

---

## 5) Yêu cầu 3 — Chạy retrieval cho từng cấu hình và lưu top‑k

### 5.1 Chế độ “đúng đến yêu cầu 3” (compare-only)

Chế độ này **không in/tính metrics**, chỉ chạy retrieval và xuất log top‑k.

```bash
python RAG/eval_retrieval.py ^
  --compare-only ^
  --index-dir RAG/output_index ^
  --dataset RAG/eval_queries.auto.jsonl ^
  --top-k 5 ^
  --evidence-top-k 3 ^
  --min-support-rate 0.7 ^
  --min-supported-queries 1
```

Nếu muốn chạy nhanh trên một phần dataset:

```bash
python RAG/eval_retrieval.py --compare-only --index-dir RAG/output_index --dataset RAG/eval_queries.auto.jsonl --max-queries 50 --top-k 5
```

### 5.2 Output nằm ở đâu?

Sau mỗi lần chạy, script tạo một thư mục theo `run_id`:

- `retrieval_runs/<run_id>/run_config.json`
- `retrieval_runs/<run_id>/retrieval_logs.jsonl`
- `retrieval_runs/<run_id>/report.md` (bản xem nhanh top‑k)
- `retrieval_runs/<run_id>/evidence_summary.json` (thống kê đủ/thiếu bằng chứng theo config)
- `retrieval_runs/<run_id>/final_conclusion.md` (kết luận tự động có enforce nguyên tắc bằng chứng)

### 5.3 `retrieval_logs.jsonl` gồm những gì?

Mỗi dòng tương ứng **(query × config)** và có:
- `run_id`
- `config`
- `group`
- `query`
- `results`: list top‑k, mỗi item có đúng các trường:
  - `rank`
  - `score`
  - `chunk_id`
  - `heading`
  - `source_path`
  - `snippet`

Đây chính là dữ liệu bạn cần để làm bước 4 (chuẩn hoá citation) về sau.

### 5.4 Enforce nguyên tắc “không bằng chứng -> không kết luận”

Script hiện đã có tầng kết luận cuối theo evidence gate:

- Mỗi cặp `(query, config)` sẽ được gán trạng thái:
  - `SUPPORTED`: có citation hợp lệ trong cửa sổ `--evidence-top-k`.
  - `INSUFFICIENT_EVIDENCE`: không có citation relevant trong cửa sổ bằng chứng.
  - `NO_GROUND_TRUTH`: query không có nhãn phù hợp để kiểm chứng.
- Nếu một config không đạt ngưỡng:
  - `support_rate >= --min-support-rate`
  - `supported_queries >= --min-supported-queries`
  thì config đó **không được phép** đi tới kết luận cuối.
- Nếu không có config nào vượt ngưỡng bằng chứng, file `final_conclusion.md` sẽ ghi rõ:
  - **KHÔNG KẾT LUẬN**.

---

## 6) (Tuỳ chọn) Chạy kèm metrics (khi cần)

Nếu muốn tính `hit@k / mrr@k / ndcg@k ...` thì chạy **không có** `--compare-only`:

```bash
python RAG/eval_retrieval.py --index-dir RAG/output_index --dataset RAG/eval_queries.auto.jsonl --k 1,3,5,10 --top-k 5
```

Ví dụ đầy đủ (có metrics + evidence gate):

```bash
python RAG/eval_retrieval.py --index-dir RAG/output_index --dataset RAG/eval_queries.auto.jsonl --k 1,3,5,10 --top-k 5 --evidence-top-k 3 --min-support-rate 0.7 --min-supported-queries 1
```

Khi đó trong `retrieval_runs/<run_id>/` sẽ có thêm `summary_metrics.json`.

---

## 7) Gợi ý thực hành để dataset “đa dạng hơn”

- Tăng số query theo nhóm `khoan_va_dieu` (hay lộ lỗi clause boost/filter).
- Tránh query quá ngắn như `"Nghị định"` hoặc `"Trình"` vì quá mơ hồ, dễ kéo nhiễu.
- Với `ngu_nghia_rong`, nên dùng câu mô tả rõ ý (10–20 từ) thay vì 1–2 từ khoá.

