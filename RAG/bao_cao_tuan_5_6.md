# Báo cáo tuần 5-6: Xây dựng Index + Retrieval và demo truy suất theo Điều/Khoản

## 1. Mục tiêu tuần 5-6
Trong tuần này, nhóm tập trung hoàn thiện lớp truy suất của hệ RAG trên dữ liệu pháp lý tiếng Việt, bao gồm:
- Hoàn chỉnh pipeline tạo chỉ mục vector (index) từ tài liệu pháp lý.
- Bổ sung cơ chế truy vấn (retrieval) theo ngữ nghĩa và ưu tiên theo cấu trúc pháp lý Điều/Khoản.
- Tạo chế độ báo cáo cơ sở dữ liệu và kết quả truy vấn mẫu để phục vụ demo.

Kết quả hướng tới là một pipeline chạy được đầu-cuối:
- `index`: xây cơ sở dữ liệu vector.
- `query`: truy xuất top-k đoạn liên quan.
- `report`: xuất báo cáo kỹ thuật và truy vấn demo.

---

## 2. Liên hệ với các tuần trước
### 2.1 Kế thừa từ tuần 1-2
- Giữ nguyên định hướng mô hình: embedding `BAAI/bge-m3`, vector store `FAISS`.
- Bám nguyên tắc RAG: chỉ kết luận dựa trên bằng chứng truy suất được.

### 2.2 Kế thừa từ tuần 3-4
- Tái sử dụng pipeline ingestion/normalization/chunking theo cấu trúc pháp lý.
- Tiếp tục dùng metadata theo từng chunk để truy vết nguồn trích dẫn.

### 2.3 Mở rộng ở tuần 5-6
- Bổ sung truy vấn chuyên biệt theo Điều/Khoản.
- Bổ sung thuật toán lọc + tăng điểm cho chunk chứa tham chiếu pháp lý trong câu hỏi.
- Bổ sung cơ chế xuất báo cáo tự động bằng JSON.

---

## 3. Kiến trúc kỹ thuật triển khai tuần này
Kiến trúc xử lý gồm 2 pha chính:

1. Pha offline (Indexing)
- Đọc tài liệu (`.txt`, `.docx`, `.doc`).
- Chuẩn hóa văn bản.
- Chunking theo heading pháp lý + tách đoạn dài bằng cửa sổ trượt.
- Sinh embedding cho từng chunk.
- Lưu chỉ mục FAISS và metadata.

2. Pha online (Retrieval)
- Nhận câu hỏi người dùng.
- Nhận diện tham chiếu Điều/Khoản trong câu hỏi.
- Encode query thành vector.
- Tìm ứng viên từ FAISS.
- Lọc/rerank theo mức khớp Điều/Khoản.
- Trả top-k đoạn làm bằng chứng.

---

## 4. Ý tưởng và thuật toán theo từng bước kỹ thuật

## 4.1 Bước 1 - Đọc dữ liệu đa định dạng
### Ý tưởng
Đưa mọi tài liệu về dạng text thống nhất để xử lý sau đó không phụ thuộc định dạng gốc.

### Thuật toán xử lý
1. Duyệt đệ quy toàn bộ file trong thư mục input.
2. Chỉ nhận các đuôi hỗ trợ: `.doc`, `.docx`, `.txt`.
3. Chọn hàm đọc theo định dạng:
- `.docx`: đọc theo paragraph và nối dòng.
- `.doc`: đọc qua `textract` (optional dependency).
- `.txt`: đọc UTF-8 với fallback `errors='ignore'`.
4. Gắn `doc_id = file_path.stem` và lưu `source_path`.

---

## 4.2 Bước 2 - Chuẩn hóa văn bản (Normalization)
### Ý tưởng
Giảm nhiễu định dạng nhưng giữ nguyên nội dung pháp lý cốt lõi để không làm sai nghĩa điều khoản.

### Thuật toán xử lý
1. Chuẩn hóa xuống dòng: `\r\n`, `\r` -> `\n`.
2. Gom khoảng trắng/tab thừa thành 1 khoảng trắng.
3. Gom nhiều dòng trống liên tiếp thành tối đa 2 dòng trống.
4. Cắt khoảng trắng đầu/cuối tài liệu.

---

## 4.3 Bước 3 - Tách cấu trúc theo Điều/Khoản/Mục
### Ý tưởng
Tận dụng cấu trúc tự nhiên của văn bản pháp luật để tạo chunk có nghĩa pháp lý rõ ràng.

### Thuật toán xử lý
1. Dùng regex heading:
- `^(Điều|Dieu|Khoản|Khoan|Mục|Muc) ...`
2. Quét từng dòng:
- Nếu là heading mới: flush chunk hiện tại, mở chunk mới.
- Nếu không: nối vào chunk hiện tại.
3. Mỗi section giữ thông tin:
- `heading`, `text`, `order`.

---

## 4.4 Bước 4 - Chia đoạn dài bằng sliding window
### Ý tưởng
Nếu section quá dài thì chia nhỏ để tăng chất lượng embedding và retrieval, nhưng vẫn giữ ngữ cảnh bằng overlap.

### Thuật toán xử lý
Với text có `N` từ:
1. Nếu `N <= max_words`: giữ nguyên 1 chunk.
2. Nếu `N > max_words`:
- `step = max_words - overlap_words`.
- Tạo các cửa sổ `[i, i + max_words)` với `i += step`.
3. Bỏ các chunk quá ngắn (`< min_words`) để giảm nhiễu.

Tham số đang dùng trong thử nghiệm:
- `max_words = 600`
- `overlap_words = 80`
- `min_words = 40`

---

## 4.5 Bước 5 - Embedding và lập chỉ mục FAISS
### Ý tưởng
Biểu diễn mỗi chunk thành vector ngữ nghĩa để hỗ trợ truy vấn tương đồng ngữ cảnh thay vì so khớp từ khóa cứng.

### Thuật toán xử lý
1. Tải model embedding (`BAAI/bge-m3`).
2. Encode batch các chunk:
- `normalize_embeddings=True`.
3. Dùng `FAISS IndexFlatIP` để lưu vector.
- Vì vector đã chuẩn hóa, inner product tương đương cosine similarity.
4. Ghi ra 3 artifact:
- `output_index/index.faiss`
- `output_index/metadata.jsonl`
- `output_index/manifest.json`

---

## 4.6 Bước 6 - Truy vấn theo Điều/Khoản (Clause-aware retrieval)
### Ý tưởng
Ngoài tương đồng ngữ nghĩa, cần tăng độ chính xác cho truy vấn pháp lý bằng cách nhận diện và ưu tiên các tham chiếu Điều/Khoản trong câu hỏi.

### Thuật toán xử lý
1. Chuẩn hóa text query để so khớp linh hoạt:
- Hạ chữ thường.
- Bỏ dấu tiếng Việt (NFD, bỏ ký tự `Mn`).
- Chuẩn hóa khoảng trắng.
2. Trích xuất tham chiếu pháp lý từ query:
- Mẫu `khoan X dieu Y`.
- Mẫu `dieu Y`.
3. Encode query thành vector.
4. Tìm `candidate_k` từ FAISS:
- `candidate_k = min(max(top_k*4, top_k), total_chunks)`.
5. Với từng candidate:
- Nếu bật `--clause-filter`: chỉ giữ chunk chứa tham chiếu Điều/Khoản tương ứng.
- Tính điểm cuối:
  - `final_score = faiss_score + boost`
  - boost `+0.25` nếu match trong heading
  - boost `+0.10` nếu match trong body
6. Sắp xếp giảm dần theo `final_score` và lấy top-k.

Ghi chú:
- Cách này là lexical-boost đơn giản, dễ giải thích, phù hợp báo cáo kỹ thuật.
- Có thể nâng cấp bằng cross-encoder reranker ở giai đoạn tiếp theo.

---

## 4.7 Bước 7 - Báo cáo cơ sở dữ liệu và truy vấn
### Ý tưởng
Cung cấp một chế độ `report` để tự động tổng hợp số liệu kỹ thuật + kết quả demo nhằm phục vụ đánh giá và trình bày.

### Thuật toán xử lý
1. Nạp `index.faiss` + `metadata.jsonl`.
2. Tính thống kê DB:
- số vector, số chiều vector, số chunk, số tài liệu,
- độ phủ heading,
- độ dài chunk trung bình/nhỏ nhất/lớn nhất,
- top heading xuất hiện nhiều.
3. Chạy danh sách demo query.
4. Lưu mỗi query gồm:
- rank, score, chunk_id, heading, source_path, snippet.
5. Xuất JSON ra file báo cáo.

---

## 5. Cú pháp lệnh và chế độ chạy
Script hỗ trợ 3 command chính:

1. Build index:
```bash
python rag_pipeline.py index --input-dir input_docs --output-dir output_index
```

2. Query trực tiếp:
```bash
python rag_pipeline.py query --index-dir output_index --query "Điều 8 trình tự đầu tư dự án" --top-k 5 --clause-filter
```

3. Sinh báo cáo:
```bash
python rag_pipeline.py report --index-dir output_index --top-k 3 --clause-filter \
  --demo-query "Điều 8 trình tự đầu tư dự án" \
  --demo-query "khoản 2 điều 7 dự án mua sắm" \
  --demo-query "Điều 10 quyết định chủ trương đầu tư" \
  --output-file bao_cao_truy_van.json
```

---

## 6. Kết quả thực nghiệm tuần này (theo báo cáo chạy thật)
Nguồn số liệu: `bao_cao_truy_van.json`.

### 6.1 Thống kê cơ sở dữ liệu vector
- Số vector: 280
- Số chiều vector: 1024
- Số chunk: 280
- Số tài liệu: 4
- Chunk có heading: 276 (coverage 98.57%)
- Độ dài chunk trung bình: 351.52 từ
- Độ dài min/max: 40 / 600 từ

### 6.2 Kết quả truy vấn demo theo Điều/Khoản
1. Query: "Điều 8 trình tự đầu tư dự án"
- Rank 1 trả về chunk heading `Điều 8. Trình` (đúng trọng tâm).

2. Query: "khoản 2 điều 7 dự án mua sắm"
- Top kết quả có chứa ngữ cảnh dự án mua sắm và tham chiếu điều khoản liên quan.

3. Query: "Điều 10 quyết định chủ trương đầu tư"
- Rank 1 trả về chunk heading `Điều 10.` (đúng trọng tâm).

Nhận xét nhanh:
- Pipeline truy suất theo ngữ nghĩa hoạt động tốt với truy vấn Điều cụ thể.
- Với truy vấn Khoản + Điều, đã có cải thiện nhờ clause filter/boost, nhưng vẫn còn dư địa tăng precision ở top-1.

---

## 7. Đánh giá kỹ thuật
### 7.1 Điểm mạnh
- Quy trình end-to-end chạy ổn định: index -> query -> report.
- Dễ mở rộng và dễ audit nhờ metadata + JSON báo cáo.
- Có cơ chế gắn ngữ cảnh pháp lý Điều/Khoản thay vì chỉ semantic search thuần túy.

### 7.2 Hạn chế hiện tại
- Heading extraction phụ thuộc chất lượng text đầu vào; tài liệu nhiễu có thể tách chưa tối ưu.
- Cơ chế boost hiện là heuristic tuyến tính, chưa phải reranking sâu.
- Chưa có bộ nhãn chuẩn để đo Recall@k/MRR định lượng đầy đủ.

---

## 8. Rủi ro và hướng giảm thiểu
1. Rủi ro OCR/nhiễu định dạng
- Giảm thiểu: tăng bước làm sạch, loại phần menu/trang web thừa ở đầu văn bản.

2. Rủi ro truy suất nhầm điều khoản gần nghĩa
- Giảm thiểu: tăng trọng số match Điều/Khoản; thêm regex chuẩn hóa số điều.

3. Rủi ro mở rộng dữ liệu làm giảm tốc độ
- Giảm thiểu: cân nhắc FAISS IVF/HNSW khi dữ liệu lớn hơn.

---

## 9. Kế hoạch tuần tiếp theo
1. Tối ưu chất lượng retrieval
- Thêm reranker cross-encoder cho top-n candidate.
- Thiết kế benchmark định lượng: Recall@k, MRR, nDCG.

2. Tối ưu dữ liệu pháp lý
- Bổ sung bước loại bỏ nội dung nhiễu (menu, quảng cáo, chú thích hệ thống).
- Chuẩn hóa mạnh hơn cho mô hình heading/điều-khoản.

3. Kết nối LLM sinh báo cáo thay đổi
- Dùng top-k evidence làm ngữ cảnh đầu vào cho LLM.
- Bắt buộc trích dẫn nguồn `chunk_id` và `source_path` trong kết luận.

---

## 10. Kết luận tuần 5-6
Tuần 5-6 đã hoàn thành mục tiêu trọng tâm: hiện thực hóa lớp Index + Retrieval cho bài toán pháp lý tiếng Việt, đồng thời triển khai cơ chế truy suất theo Điều/Khoản và xuất báo cáo kỹ thuật tự động. Nền tảng này đủ vững để chuyển sang giai đoạn tối ưu chất lượng truy suất và tích hợp lớp tổng hợp bằng LLM ở các tuần tiếp theo.
