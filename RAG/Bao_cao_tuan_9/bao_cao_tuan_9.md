# Báo cáo tuần 9: Xây dựng UI bản 1 — Chatbot Web So Sánh Văn Bản Pháp Lý

## 1. Mục tiêu tuần 9

Theo đề cương dự án, tuần 9 yêu cầu:

> **UI bản 1 (upload, xem song song, kết quả theo mục)** — Sản phẩm bàn giao: **Báo cáo chatbot**

Nhóm tập trung xây dựng giao diện web chạy cục bộ (local) với các chức năng:

1. **Upload tài liệu**: Nhập 2 tài liệu DOCX/TXT để so sánh.
2. **Xem song song**: Hiển thị đồng thời nội dung 2 tài liệu.
3. **Kết quả so sánh theo mục**: Phát hiện thay đổi (thêm/xóa/sửa) theo Điều/Khoản, có highlight chi tiết.
4. **Chatbot hỏi-đáp RAG**: Người dùng nhập câu hỏi, hệ thống truy vấn và trả kết quả có trích dẫn nguồn.

---

## 2. Liên hệ với các tuần trước

### 2.1 Kế thừa từ tuần 1–4
- Pipeline ingestion → chuẩn hóa → chunking theo Điều/Khoản → FAISS index.
- Embedding model `BAAI/bge-m3`, vector store FAISS IndexFlatIP.
- Metadata tracking: `chunk_id`, `doc_id`, `source_path`, `heading`, `order`.

### 2.2 Kế thừa từ tuần 5–6
- Retrieval engine: semantic search + clause-aware boost/filter.
- Modul truy vấn theo Điều/Khoản (`retrieve_chunks()`).

### 2.3 Kế thừa từ tuần 7–8
- Sinh báo cáo so sánh + citation với nguyên tắc "không bằng chứng → không kết luận".
- Evidence gate: `SUPPORTED` / `INSUFFICIENT_EVIDENCE` / `NO_GROUND_TRUTH`.
- Bộ đánh giá retrieval 3 cấu hình (`eval_retrieval.py`).

### 2.4 Mở rộng ở tuần 9
- Xây dựng giao diện web bằng **Flask** + HTML/CSS/JS.
- Thêm **module so sánh tài liệu** (`compare_engine.py`) phát hiện diff theo cấu trúc pháp lý.
- Tích hợp **Ollama** (Local LLM) để sinh câu trả lời tự nhiên có trích dẫn.
- Giao diện chatbot với hiển thị citation bắt buộc.

---

## 3. Kiến trúc hệ thống tuần 9

```
┌────────────────────────────────────────────────────────────┐
│                    BROWSER (localhost:5000)                 │
│  ┌──────────┐   ┌───────────────┐   ┌──────────────────┐  │
│  │  Upload   │   │   So sánh     │   │    Chatbot       │  │
│  │ (Tab 1)   │   │   (Tab 2)     │   │    (Tab 3)       │  │
│  └─────┬─────┘   └──────┬────────┘   └───────┬──────────┘  │
└────────┼────────────────┼────────────────────┼──────────────┘
         │                │                    │
    POST /api/upload  POST /api/compare    POST /api/chat
         │                │                    │
┌────────▼────────────────▼────────────────────▼──────────────┐
│                    FLASK BACKEND (app.py)                    │
│                                                              │
│   ┌──────────────┐  ┌────────────────┐  ┌───────────────┐   │
│   │ rag_pipeline │  │ compare_engine │  │   Ollama API  │   │
│   │  (retrieval) │  │ (diff engine)  │  │  (Local LLM)  │   │
│   └──────┬───────┘  └───────┬────────┘  └───────┬───────┘   │
│          │                  │                    │            │
│   ┌──────▼──────┐    ┌─────▼─────┐      ┌──────▼──────┐    │
│   │ FAISS Index │    │  difflib  │      │ qwen2.5:7b  │    │
│   │ + metadata  │    │SequMatch  │      │ (hoặc khác) │    │
│   └─────────────┘    └───────────┘      └─────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Chi tiết kỹ thuật từng thành phần

### 4.1 Module so sánh tài liệu (`compare_engine.py`)

#### Ý tưởng
So sánh 2 tài liệu pháp lý **theo cấu trúc** thay vì so toàn văn. Mỗi Điều/Khoản được ghép cặp và so sánh riêng.

#### Thuật toán
1. **Chia đoạn theo heading**: Dùng regex `HEADING_RE` (kế thừa từ `rag_pipeline.py`) để tách từng section có heading `Điều X`, `Khoản Y`, `Mục Z`.
2. **Chuẩn hóa heading key**: Trích xuất prefix + số để ghép cặp chính xác (ví dụ `"Điều 5."` → `"điều_5"`).
3. **Ghép cặp**: Duyệt tất cả heading key từ cả 2 tài liệu, xác định mục nào có ở cả 2, mục nào chỉ có ở 1.
4. **So sánh nội dung**:
   - Dùng `difflib.SequenceMatcher` tính tỉ lệ similarity.
   - Nếu similarity ≥ 98%: đánh dấu `UNCHANGED`.
   - Nếu < 98%: đánh dấu `MODIFIED`, tính inline diff (từng từ).
   - Mục chỉ có ở bản mới: `ADDED`.
   - Mục chỉ có ở bản gốc: `REMOVED`.
5. **Inline diff**: Tách text theo từ, chạy `SequenceMatcher.get_opcodes()` để tìm `equal`, `insert`, `delete`, `replace`.

#### Output
Mỗi mục trả về:
- `heading`: tên Điều/Khoản
- `diff_type`: `added|removed|modified|unchanged`
- `old_text`, `new_text`: nội dung gốc và sửa đổi
- `similarity`: tỉ lệ giống nhau (0.0 → 1.0)
- `inline_diffs`: danh sách thay đổi chi tiết (tag + old_text + new_text)

---

### 4.2 Flask Backend (`app.py`)

#### Các API endpoint

| Endpoint | Method | Chức năng |
|---|---|---|
| `/` | GET | Phục vụ giao diện web |
| `/api/status` | GET | Trạng thái hệ thống (doc loaded, Ollama available, model name) |
| `/api/upload` | POST | Upload 1-2 file, đọc + normalize + chunk + build FAISS index tạm |
| `/api/documents` | GET | Lấy nội dung 2 tài liệu đã upload (cho xem song song) |
| `/api/compare` | POST | Chạy so sánh 2 tài liệu, trả danh sách diff theo mục |
| `/api/chat` | POST | Nhận câu hỏi → retrieval RAG → (tùy chọn) LLM → trả answer + citations |
| `/api/reset` | POST | Reset trạng thái phiên làm việc |

#### Luồng xử lý Upload
1. Nhận file từ form-data.
2. Lưu vào thư mục `uploads/`.
3. Đọc file (DOCX qua `python-docx`, TXT qua UTF-8).
4. Chuẩn hóa text (`normalize_text()`).
5. Chunk document (`chunk_document()`).
6. Build embedding + FAISS index tạm cho phiên làm việc.

#### Luồng xử lý Chat (RAG)
1. Nhận câu hỏi từ người dùng.
2. Truy vấn top-5 chunk liên quan bằng `retrieve_chunks()`.
3. Nếu **Ollama đang chạy**: gửi context + câu hỏi đến LLM local, nhận câu trả lời tự nhiên.
4. Nếu **Ollama không khả dụng**: format kết quả retrieval thuần làm câu trả lời.
5. Trả JSON gồm: `answer`, `citations`, `evidence_status`, `llm_used`, `llm_model`.

#### Tích hợp Ollama (Local LLM)
- Kiểm tra Ollama qua API `GET /api/tags` (timeout 3s).
- Gọi `POST /api/generate` với:
  - System prompt: hướng dẫn trợ lý trả lời dựa hoàn toàn vào ngữ cảnh, trích dẫn nguồn.
  - User prompt: context (top-3 chunk) + câu hỏi.
  - `temperature=0.3`, `num_predict=1024`.
- Tự động fallback sang retrieval thuần nếu Ollama lỗi hoặc chưa cài.

---

### 4.3 Giao diện Web (Frontend)

#### Thiết kế tổng quan
- **Single-page app** với 3 tab: Upload | So sánh | Chatbot.
- **Dark mode** mặc định với glassmorphism.
- **Font**: Inter (Google Fonts).
- **Color scheme**: gradient tím-xanh chủ đạo, semantic colors cho diff.
- **Responsive**: Tương thích mobile.
- **Micro-animations**: fade-in cho tab, bounce cho typing indicator, scale cho hover.

#### Tab 1 — Upload

[PLACEHOLDER: Ảnh chụp giao diện tab Upload]

Chức năng:
- 2 khu vực **drag-and-drop** cho tài liệu 1 (bản gốc) và tài liệu 2 (bản sửa đổi).
- Hỗ trợ kéo thả hoặc click chọn file.
- Hiển thị trạng thái file đã chọn (tên file, nút xóa).
- Nút "Upload & Xử lý": gửi file lên server, hiển thị kết quả (số chunks được tạo).

#### Tab 2 — So sánh

[PLACEHOLDER: Ảnh chụp giao diện tab So sánh — tổng quan stats]

[PLACEHOLDER: Ảnh chụp kết quả diff chi tiết — mục Modified với inline diff]

Chức năng:
- **Bảng thống kê**: hiển thị tổng mục, số mục sửa đổi/thêm/xóa/giữ nguyên.
- **Bộ lọc**: Tất cả | Sửa đổi | Thêm mới | Đã xóa | Giữ nguyên.
- **Danh sách diff**: mỗi mục hiển thị:
  - Badge trạng thái (🟡 Sửa / 🟢 Thêm / 🔴 Xóa / ⚪ Giữ nguyên).
  - Heading (tên Điều/Khoản).
  - Tỉ lệ similarity (cho mục Modified).
  - Nội dung song song (bản gốc vs bản sửa đổi) khi mở rộng.
  - **Inline highlighting**: chữ bị xóa gạch ngang đỏ, chữ thêm mới xanh lá.
- **Ưu tiên hiển thị**: Sửa đổi → Thêm → Xóa hiện trước; Giữ nguyên xếp cuối với style mờ.

#### Tab 3 — Chatbot

[PLACEHOLDER: Ảnh chụp giao diện Chatbot — câu hỏi và trả lời có citation]

Chức năng:
- Giao diện chat dạng bubble (user → bot).
- **Quick chips**: câu hỏi mẫu để thử nhanh.
- **Câu trả lời** từ bot kèm:
  - Nội dung trả lời (từ LLM hoặc retrieval thuần).
  - **Evidence tag**: `✓ Có bằng chứng` hoặc `⚠ Thiếu bằng chứng`.
  - **Tag nguồn**: LLM model name hoặc "Retrieval thuần".
  - **Danh sách citation**: rank, score, heading, source, snippet (click để mở rộng).
- **Typing indicator**: animation 3 chấm khi chờ phản hồi.
- **Status bar**: hiển thị trạng thái Ollama (online/offline).

---

## 5. Cấu trúc file dự án (sau tuần 9)

```
RAG/
├── app.py                          # [NEW] Flask server
├── compare_engine.py               # [NEW] Module so sánh tài liệu
├── templates/
│   └── index.html                  # [NEW] Frontend HTML
├── static/
│   ├── style.css                   # [NEW] CSS (dark mode, glassmorphism)
│   └── app.js                      # [NEW] JavaScript logic
├── uploads/                        # [NEW] Thư mục lưu file upload (runtime)
├── rag_pipeline.py                 # Pipeline RAG (tuần 3–6)
├── retrieval.py                    # Retrieval CLI (tuần 5–6)
├── eval_retrieval.py               # Đánh giá retrieval (tuần 7–8)
├── compare_engine.py               # Module so sánh tài liệu
├── crawl_thuvienphapluat.py        # Crawler dữ liệu (tuần 3–4)
├── input_docs/                     # 104 văn bản pháp lý
├── output_index/                   # FAISS index + metadata
├── retrieval_runs/                 # Kết quả đánh giá retrieval
├── requirements.txt                # Dependencies (thêm flask)
└── copilot-instructions.md         # Đề cương dự án
```

---

## 6. Cách chạy hệ thống

### 6.1 Khởi động cơ bản (không cần LLM)
```bash
conda activate PROPTIT_AI
cd d:\Dean'sCode\TTCS\RAG
python app.py
```
Truy cập: `http://localhost:5000`

### 6.2 Khởi động với LLM local (Ollama)
```bash
# Terminal 1: chạy Ollama
ollama serve
ollama pull qwen2.5:7b

# Terminal 2: chạy web app
conda activate PROPTIT_AI
python app.py
```
Khi Ollama sẵn sàng, chatbot sẽ tự động dùng LLM để sinh câu trả lời tự nhiên.

---

## 7. Demo kết quả

### 7.1 Demo Upload

[PLACEHOLDER: Ảnh chụp upload 2 file thành công, hiển thị số chunks]

### 7.2 Demo So sánh

[PLACEHOLDER: Ảnh chụp bảng thống kê (tổng/sửa/thêm/xóa/giữ nguyên)]

[PLACEHOLDER: Ảnh chụp diff Điều cụ thể — bản gốc vs bản sửa đổi với highlight]

### 7.3 Demo Chatbot

[PLACEHOLDER: Ảnh chụp hỏi "Điều 5 quy định nội dung gì?" — trả lời + citation]

[PLACEHOLDER: Ảnh chụp hỏi "Khoản 1 Điều 8 có nội dung gì?" — trả lời + citation]

---

## 8. Đánh giá kỹ thuật

### 8.1 Điểm mạnh
- **Chạy hoàn toàn offline/local**: không gửi dữ liệu ra bên ngoài, đảm bảo bảo mật.
- **Tích hợp liền mạch**: tái sử dụng toàn bộ pipeline RAG từ các tuần trước.
- **So sánh có cấu trúc**: diff theo Điều/Khoản thay vì diff toàn văn, phù hợp bài toán pháp lý.
- **LLM fallback**: tự động chuyển giữa LLM và retrieval thuần, không bị phụ thuộc.
- **Citation bắt buộc**: mọi câu trả lời đều kèm trích dẫn nguồn cụ thể.
- **Giao diện hiện đại**: dark mode, glassmorphism, responsive, micro-animations.

### 8.2 Hạn chế hiện tại
- **Single-user**: session in-memory phục vụ 1 người dùng (phù hợp prototype local).
- **Chưa hỗ trợ PDF**: chỉ đọc DOCX và TXT (đề cương ưu tiên DOCX/text).
- **So sánh heading-based**: phụ thuộc chất lượng heading extraction; văn bản không theo chuẩn pháp lý sẽ so sánh kém chính xác hơn.
- **LLM phụ thuộc Ollama**: cần cài thêm nếu muốn dùng LLM.

---

## 9. Rủi ro và hướng giảm thiểu

| Rủi ro | Mức | Hướng giảm thiểu |
|---|---|---|
| File upload quá lớn (>50MB) | Thấp | Đã giới hạn `MAX_CONTENT_LENGTH = 50MB` |
| Ollama chưa cài/chưa chạy | Trung bình | Tự động fallback sang retrieval thuần, UI thông báo rõ |
| Heading extraction sai | Trung bình | Cải thiện regex, thêm heuristic cho heading không chuẩn |
| LLM sinh thông tin sai (hallucination) | Trung bình | System prompt ép trả lời dựa vào context, evidence gate kiểm chứng |
| Thời gian embedding lâu với file lớn | Thấp | Chunking giới hạn max_words, batch encoding |

---

## 10. Kế hoạch tuần tiếp theo (tuần 10)

Theo đề cương: **Xây dựng tập dữ liệu + baseline; chạy đánh giá vòng 1.**

1. **Xây dựng tập dữ liệu mẫu**:
   - Chuẩn bị 10–20 cặp tài liệu có chỉnh sửa biết trước.
   - Gán nhãn ground-truth cho từng cặp (thay đổi nào, ở Điều nào).

2. **Baseline đánh giá**:
   - Chạy comparison engine trên tập dữ liệu mẫu.
   - Đo precision/recall phát hiện thay đổi.
   - Đo chất lượng retrieval trên bộ query mở rộng.

3. **Cải thiện UI** (nếu cần):
   - Bổ sung tính năng export kết quả so sánh (PDF/Markdown).
   - Cải thiện UX dựa trên feedback thực tế.

---

## 11. Kết luận tuần 9

Tuần 9 đã hoàn thành mục tiêu trọng tâm: xây dựng **giao diện web bản 1** cho hệ thống so sánh văn bản pháp lý. Hệ thống hỗ trợ đầy đủ luồng: upload tài liệu → so sánh theo Điều/Khoản → chatbot hỏi-đáp RAG có trích dẫn nguồn. Toàn bộ chạy cục bộ, đảm bảo bảo mật dữ liệu. Nền tảng UI này đủ để chuyển sang giai đoạn xây dựng tập dữ liệu đánh giá và chạy baseline ở tuần 10.
