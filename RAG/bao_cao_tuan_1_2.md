# Báo cáo tuần 1-2: Tổng quan và lựa chọn mô hình RAG + LLM (bản chi tiết)

## 1. Mục tiêu
Trong hai tuần đầu, mục tiêu chính là xây dựng nền tảng lý thuyết và lựa chọn cấu hình mô hình phù hợp cho bài toán so sánh văn bản pháp lý tiếng Việt theo hướng chạy cục bộ. Cụ thể:
- Tổng hợp đầy đủ các thành phần của một hệ thống RAG phục vụ trích dẫn và giải thích thay đổi.
- Xác định tiêu chí lựa chọn mô hình (embedding, LLM, vector store, reranker) phù hợp với ràng buộc dữ liệu nội bộ.
- Đề xuất cấu hình ban đầu có thể triển khai nhanh để phục vụ thí nghiệm ở các tuần tiếp theo.

## 2. Bối cảnh bài toán và yêu cầu đầu ra
Hệ thống nhận đầu vào là hai văn bản hợp đồng/phụ lục (PDF/DOCX) và tạo báo cáo thay đổi ở mức điều khoản. Đầu ra cần:
- Liệt kê thay đổi theo nhóm: thêm mới, xóa bỏ, chỉnh sửa nội dung.
- Đính kèm trích dẫn bằng chứng ở dạng đoạn văn/điều khoản gốc.
- Giải thích ngắn gọn, tránh suy diễn. Nếu không có bằng chứng từ tài liệu thì không kết luận.

Các yêu cầu phi chức năng gồm:
- Dữ liệu nhạy cảm nên phải chạy local, không gửi ra ngoài.
- Tốc độ xử lý chấp nhận được trên GPU tầm trung hoặc CPU mạnh.
- Dễ triển khai, có thư viện hỗ trợ tốt.

## 3. Tổng quan hệ thống RAG đề xuất
Quy trình tổng thể gồm các bước sau:
1. Trích xuất văn bản: đọc PDF/DOCX, tách văn bản thô.
2. Chuẩn hóa: làm sạch ký tự, chuẩn hóa dấu câu, tiêu đề, xuống dòng.
3. Tách đoạn (chunking): chia theo điều khoản/tiêu đề để giữ ngữ nghĩa pháp lý.
4. Lập chỉ mục: tạo embedding cho mỗi đoạn và lưu vào vector store.
5. Truy suất: nhận truy vấn theo điều khoản hoặc theo cặp đoạn tương ứng, lấy top-k.
6. Tổng hợp: LLM tổng hợp thay đổi kèm trích dẫn bằng chứng.

Nguyên tắc kiểm soát chất lượng: không có bằng chứng rõ ràng thì không kết luận.

## 4. Tiêu chí lựa chọn mô hình
### 4.1 Tiêu chí chung
- Chạy cục bộ, không phụ thuộc dịch vụ đám mây.
- Hỗ trợ tiếng Việt tốt, ổn định trong trích dẫn đoạn văn.
- Dễ tích hợp với Python và các thư viện phổ biến.
- Có phiên bản quantized để chạy trên máy cá nhân.

### 4.2 Tiêu chí cho embedding
- Độ chính xác truy suất cho ngôn ngữ đa dạng, đặc biệt tiếng Việt.
- Khả năng mô tả ngữ nghĩa dài, câu pháp lý nhiều mệnh đề.
- Tốc độ tạo embedding và kích thước vector phù hợp.

### 4.3 Tiêu chí cho LLM
- Khả năng tuân thủ chỉ dẫn, hạn chế suy diễn.
- Sinh văn bản tiếng Việt tự nhiên và chính xác.
- Hỗ trợ trích dẫn và nêu bằng chứng.

### 4.4 Tiêu chí cho vector store và reranker
- Vector store: nhẹ, dễ tích hợp, không yêu cầu hạ tầng nặng.
- Reranker: tăng độ chính xác top-k, giảm nhiễu khi nhiều đoạn tương tự.

## 5. Lựa chọn mô hình chi tiết
### 5.1 Embedding
**Ứng cử viên:**
- BGE-M3 (multilingual)
- multilingual-e5-large hoặc e5-base

**Lựa chọn:** BGE-M3

**Lý do:**
- Hỗ trợ đa ngôn ngữ, hiệu quả tốt cho tiếng Việt trong truy suất ngữ nghĩa.
- Dễ tích hợp qua Hugging Face, có tài liệu sử dụng rõ ràng.
- Cho phép dùng chung với reranker họ bge để đồng bộ pipeline.

### 5.2 LLM
**Ứng cử viên:**
- Qwen2.5-7B-Instruct
- Llama 3.1 8B Instruct

**Lựa chọn:** Qwen2.5-7B-Instruct

**Lý do:**
- Khả năng tiếng Việt tốt và tuân thủ hướng dẫn cao.
- Có bản quantized chạy tốt trên GPU tầm trung hoặc CPU.
- Dễ triển khai qua llama.cpp/gguf hoặc transformers.

### 5.3 Vector store
**Ứng cử viên:** FAISS, Chroma

**Lựa chọn:** FAISS

**Lý do:**
- Nhẹ, chạy local, phù hợp cho giai đoạn nghiên cứu.
- Tốc độ truy suất tốt, cộng đồng hỗ trợ rộng.

### 5.4 Reranker (tùy chọn)
**Ứng cử viên:** bge-reranker-base

**Mục tiêu:** sắp xếp lại top-k đoạn truy suất để tăng độ chính xác trích dẫn và giảm nhiễu.

## 6. Thiết kế pipeline chi tiết
### 6.1 Trích xuất và chuẩn hóa
- Ưu tiên thư viện đọc DOCX/PDF ổn định để giảm lỗi ký tự.
- Chuẩn hóa định dạng tiêu đề điều khoản, tránh mất cấu trúc.
- Loại bỏ ký tự thừa, giữ nguyên nội dung pháp lý quan trọng.

### 6.2 Chunking theo điều khoản
- Chia theo tiêu đề và số điều khoản (ví dụ: Điều 1, 2.1, 2.2...).
- Độ dài mỗi chunk cần vừa đủ chứa ngữ cảnh pháp lý.
- Nếu điều khoản quá dài, tách nhỏ theo mục con nhưng giữ liên kết ngữ nghĩa.

### 6.3 Truy suất và rerank
- Tạo embedding cho từng chunk và lưu FAISS.
- Truy suất top-k theo điều khoản tương ứng hoặc theo truy vấn tổng quát.
- Dùng reranker để sắp xếp lại top-k, ưu tiên đoạn có mức tương đồng cao nhất.

### 6.4 Tổng hợp báo cáo bằng LLM
- Prompt nhấn mạnh: chỉ kết luận khi có trích dẫn.
- Bắt buộc nêu rõ phần nào được thêm, xóa, hoặc sửa.
- Trích dẫn cụ thể từ tài liệu gốc để minh chứng.

## 7. Kế hoạch thí nghiệm ban đầu
### 7.1 Bộ dữ liệu thử nghiệm
- 10-20 cặp tài liệu có thay đổi rõ ràng ở mức điều khoản.
- Bao gồm các trường hợp: sửa nhẹ câu chữ, thêm mục mới, xóa mục cũ.

### 7.2 Chỉ số đánh giá
- Độ chính xác phát hiện thay đổi (thêm/xóa/sửa).
- Tỷ lệ kết luận có trích dẫn đúng.
- Tỷ lệ bỏ sót (missing) và tỷ lệ cảnh báo sai (false positive).

### 7.3 So sánh cấu hình
- (A) BGE-M3 + Qwen2.5-7B
- (B) e5-base + Llama 3.1 8B

Mục tiêu so sánh là độ chính xác trích dẫn và độ tin cậy khi tổng hợp.

## 8. Rủi ro và hạn chế
- Văn bản pháp lý dài và nhiều mục phụ có thể gây nhiễu khi chunking.
- Lỗi OCR hoặc lỗi trích xuất PDF dễ làm sai nghĩa điều khoản.
- LLM có thể suy diễn nếu prompt chưa đủ chặt.

Biện pháp giảm rủi ro:
- Ưu tiên DOCX nếu có, hạn chế PDF scan.
- Kiểm thử chéo với các tài liệu ngắn và rõ ràng trước.
- Thiết kế prompt nhấn mạnh nguyên tắc “không bằng chứng thì không kết luận”.

## 9. Kết luận lựa chọn
- Embedding: BGE-M3
- LLM: Qwen2.5-7B-Instruct
- Vector store: FAISS
- Reranker: bge-reranker-base (tùy chọn)

Lựa chọn trên đáp ứng yêu cầu chạy local, hỗ trợ tiếng Việt và dễ triển khai. Đây là cấu hình hợp lý để bắt đầu thí nghiệm ở tuần 3-4.

## 10. Sản phẩm tuần 1-2
- Báo cáo tổng quan RAG và lựa chọn mô hình local.
- Đề xuất pipeline kỹ thuật cho bài toán so sánh hợp đồng.
- Cơ sở để triển khai thử nghiệm và đánh giá ở giai đoạn tiếp theo.
