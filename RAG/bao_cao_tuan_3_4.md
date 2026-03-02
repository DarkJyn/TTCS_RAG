# Báo cáo tuần 3-4: Quy trình nhập dữ liệu, chuẩn hóa, chunking và kiến trúc hệ thống

## 1. Mục tiêu tuần 3-4
- Xây dựng quy trình nhập dữ liệu tài liệu hợp đồng/phụ lục (TXT/DOCX) và trích xuất văn bản ổn định.
- Thiết kế chuẩn hóa văn bản và cấu trúc điều khoản để phục vụ so sánh.
- Xây dựng chiến lược chunking theo điều khoản, đảm bảo giữ ngữ nghĩa pháp lý.
- Hoàn thiện kiến trúc hệ thống và báo cáo xây dựng cơ sở dữ liệu vector embedding.

## 2. Phạm vi dữ liệu và giả định
### 2.1 Loại tài liệu
- Đầu vào gồm các tài liệu hợp đồng và phụ lục với định dạng chính: DOCX và TXT.

### 2.2 Quy mô dữ liệu thử nghiệm
- Dự kiến 10-20 cặp tài liệu có thay đổi rõ ràng ở mức điều khoản.
- Có thể mở rộng sau khi quy trình ổn định.

### 2.3 Ràng buộc
- Toàn bộ xử lý chạy local, không gửi dữ liệu ra ngoài.
- Hỗ trợ tiếng Việt và ký hiệu pháp lý (Điều, Khoản, Mục).

## 3. Quy trình nhập dữ liệu (Ingestion)
### 3.1 Kiến trúc đầu vào
- Tài liệu được lưu theo cặp (A, B) để so sánh.
- Mỗi cặp có metadata: mã hợp đồng, ngày, phiên bản, loại tài liệu.

### 3.2 Pipeline nhập dữ liệu
1. Nạp file từ thư mục theo cấu trúc chuẩn.
2. Xác định định dạng: DOCX/TXT.
3. Trích xuất văn bản thô.
4. Lưu bản text trung gian (raw text) để kiểm soát lỗi.

### 3.3 Đề xuất thư viện trích xuất
- DOCX: python-docx hoặc docx2txt.

### 3.4 Kiểm soát chất lượng nhập dữ liệu
- Kiểm tra tỷ lệ ký tự lỗi (non-UTF, ký tự rỗng).
- Thống kê số trang và độ dài văn bản để phát hiện dữ liệu bất thường.
- Lưu log cho từng file: thời gian, trạng thái, lỗi phát sinh.

## 4. Chuẩn hóa văn bản (Normalization)
### 4.1 Mục tiêu chuẩn hóa
- Giữ nguyên nội dung pháp lý nhưng loại bỏ nhiễu định dạng.
- Thống nhất cách hiển thị điều khoản và tiêu đề.
- Chuẩn hóa dấu câu, khoảng trắng, xuống dòng.

### 4.2 Các bước chuẩn hóa đề xuất
1. Chuẩn hóa mã hóa UTF-8.
2. Loại bỏ khoảng trắng thừa, tab, dòng trống liên tục.
3. Chuẩn hóa dấu câu (ví dụ: “ ; : . ,” thống nhất).
4. Chuẩn hóa tiêu đề điều khoản:
   - Nhận diện “Điều X”, “Khoản X”, “Mục X”.
   - Đưa về định dạng chuẩn để chunking.
5. Tách các tiêu đề khỏi nội dung để tạo cấu trúc phân cấp.

### 4.3 Vấn đề thường gặp và xử lý
- Văn bản bị ngắt dòng giữa câu: nối lại bằng quy tắc dòng liền kề.
- Mục lục hoặc header/footer lặp: loại bỏ theo mẫu.
- Ký hiệu pháp lý đặc biệt: giữ nguyên để tránh mất nghĩa.

## 5. Chunking theo điều khoản
### 5.1 Mục tiêu chunking
- Mỗi chunk tương ứng với một điều khoản hoặc mục pháp lý độc lập.
- Đảm bảo chunk đủ ngữ cảnh để LLM trích dẫn chính xác.

### 5.2 Chiến lược chunking
- Tách theo tiêu đề “Điều”, “Khoản”, “Mục”.
- Nếu điều khoản dài, tách theo mục con nhưng giữ liên kết.
- Không cắt giữa câu nếu không cần thiết.

### 5.3 Kích thước chunk
- Đề xuất 300-800 từ hoặc 1-3 đoạn ngắn.
- Cân bằng giữa ngữ cảnh và chi phí embedding.

### 5.4 Gắn metadata cho chunk
- Mã tài liệu, số điều, số khoản, vị trí trong văn bản.
- Loại tài liệu (hợp đồng/phụ lục).
- Mã phiên bản để phục vụ so sánh.

## 6. Kiến trúc hệ thống tổng thể
### 6.1 Thành phần chính
- Ingestion Layer: nhập dữ liệu và trích xuất văn bản.
- Normalization Layer: chuẩn hóa và cấu trúc điều khoản.
- Chunking Layer: tách đoạn, gắn metadata.
- Embedding Layer: sinh vector embedding.
- Vector Store: lưu trữ và truy vấn embedding (FAISS).
- Retrieval Layer: truy vấn top-k và rerank (tùy chọn).
- LLM Layer: tổng hợp thay đổi và trích dẫn bằng chứng.

### 6.2 Luồng dữ liệu
1. Tài liệu thô -> text chuẩn hóa.
2. Text chuẩn hóa -> danh sách chunk.
3. Chunk -> embedding -> lưu vào FAISS.
4. Truy vấn -> top-k đoạn -> LLM tổng hợp.

### 6.3 Kiểm soát chất lượng
- Lưu lại bản trung gian ở mỗi bước để audit.
- Dùng log để truy vết lỗi và kiểm thử.
- So khớp chunk với văn bản gốc để đảm bảo trích dẫn đúng.

## 7. Báo cáo xây dựng cơ sở dữ liệu vector embedding
### 7.1 Mục tiêu
- Tạo cơ sở dữ liệu vector cho từng tài liệu, phục vụ truy vấn so sánh.
- Hỗ trợ truy xuất nhanh các điều khoản có liên quan.

### 7.2 Quy trình xây dựng
1. Lấy danh sách chunk đã chuẩn hóa.
2. Tạo embedding bằng mô hình BGE-M3.
3. Lưu vector vào FAISS cùng metadata.
4. Tạo chỉ mục theo tài liệu và phiên bản.

### 7.3 Cấu trúc dữ liệu đề xuất
- Vector store: FAISS index.
- Metadata store: JSON/SQLite.
- Khóa chính: (doc_id, clause_id, chunk_id).

### 7.4 Kiểm thử ban đầu
- Thử truy vấn câu hỏi theo điều khoản.
- Đối chiếu top-k với văn bản gốc.
- Ghi nhận tỷ lệ truy xuất đúng.

## 8. Rủi ro và hướng xử lý
- Chunking sai cấu trúc điều khoản: kiểm thử với nhiều mẫu tài liệu.
- Embedding không đủ ngữ nghĩa: xem xét điều chỉnh chunk size hoặc reranker.

## 9. Kết quả dự kiến sau tuần 3-4
- Quy trình nhập dữ liệu và chuẩn hóa ổn định.
- Chunking theo điều khoản đã được thiết kế rõ ràng.
- Kiến trúc hệ thống RAG hoàn chỉnh ở mức pipeline.
- Cơ sở dữ liệu vector embedding hoạt động được trên tập dữ liệu thử nghiệm.

## 10. Định hướng tuần tiếp theo
- Tăng quy mô dữ liệu và đánh giá hiệu quả truy xuất.
- Tối ưu prompt LLM để giảm suy diễn.
- Bắt đầu so sánh định lượng giữa các cấu hình mô hình.
