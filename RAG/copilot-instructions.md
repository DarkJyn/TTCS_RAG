# Đề cương Dự án: Nghiên cứu trợ lý so sánh văn bản pháp lý chạy cục bộ (RAG + Local LLM)

## 1. Tên dự án

**Nghiên cứu trợ lý so sánh văn bản pháp lý chạy cục bộ dùng RAG + Local LLM**

## 2. Bối cảnh & Bài toán

* **Thực trạng:** Trong doanh nghiệp, việc đối chiếu 2 phiên bản hợp đồng/phụ lục thường tốn thời gian và dễ bỏ sót những thay đổi, cập nhật.
* **Nhu cầu:** Cần một công cụ hỗ trợ phát hiện khác biệt theo điều khoản, tóm tắt thay đổi, và trích dẫn bằng chứng trực tiếp từ tài liệu — đồng thời đảm bảo bảo mật bằng cách chạy **local** (cục bộ).

## 3. Mục tiêu học tập

Sau học phần, sinh viên có thể:

* Thiết kế pipeline xử lý tài liệu (PDF/DOCX → text → chunk/metadata).
* Triển khai được RAG đầy đủ công đoạn (lập chỉ mục/knowledge base: *index*, truy suất: *retrieval*, ràng buộc: *grounding*, trích dẫn: *citation*).
* Chạy mô hình LLM cục bộ.
* Xây dựng được input/output để đối chiếu tài liệu.
* Thiết kế bộ kiểm thử và đo chất lượng (*metrics, baseline*).
* Viết báo cáo kỹ thuật và trình bày demo theo tiêu chuẩn dự án doanh nghiệp.

## 4. Phạm vi & Yêu cầu

* **Input:** Nhập 2 tài liệu (hoặc 2 phiên bản) hợp đồng/phụ lục tiếng Việt; ưu tiên DOCX/text PDF.
* **Xử lý:** Chuẩn hóa, chia đoạn theo cấu trúc (tiêu đề/điều khoản/định nghĩa).
* **Công nghệ:** RAG truy suất đoạn liên quan để hỗ trợ so sánh và sinh báo cáo về các thay đổi.
* **Output:** Kết quả gồm danh sách thay đổi (thêm/xoá/sửa), tóm tắt điểm thay đổi quan trọng, và trích đoạn + vị trí.
* **Bảo mật:** Chạy **offline/local** (không gửi dữ liệu ra ngoài).
* **Giới hạn:**
* Không cần đưa ra kết luận pháp lý/tư vấn pháp luật; không đánh giá tính hợp pháp.
* Không huấn luyện mô hình từ đầu; chỉ cấu hình, tích hợp, tinh chỉnh prompt/logic.



## 5. Sản phẩm

* **Prototype chạy local:** Nhập dữ liệu → So sánh → Báo cáo + Trích dẫn (UI web tối thiểu).
* **Bộ dữ liệu mẫu:** 10-20 cặp tài liệu có chỉnh sửa biết trước.
* **Tài liệu:** Quyển báo cáo và demo cuối kỳ.

## 6. Tiêu chí chất lượng & Đánh giá

* **Độ chính xác:** Phát hiện đúng thay đổi.
* **Trích dẫn:** Tỉ lệ kết luận có trích dẫn đúng và liên quan.
* **Hiệu năng:** Thời gian xử lý/tài liệu, độ ổn định khi chạy local.
* **UX/UI:** Giao diện rõ ràng, luồng sử dụng hợp lý, thông báo lỗi/giới hạn minh bạch.

## 7. Kế hoạch theo mốc (10-12 tuần) & Sản phẩm

| Tuần | Công việc chính | Sản phẩm bàn giao |
| --- | --- | --- |
| **1-2** | Tìm hiểu tổng quan, lựa chọn được mô hình RAG + LLM. | **Báo cáo lựa chọn mô hình** |
| **3-4** | Quy trình nhập dữ liệu + chuẩn hóa + chunking; xây dựng kiến trúc hệ thống. | **Báo cáo xây dựng CSDL vector embedding** |
| **5-6** | Index + Retrieval; demo truy suất đoạn theo điều khoản. | **Báo cáo cơ sở dữ liệu và truy vấn** |
| **7-8** | Sinh báo cáo so sánh + citation; nguyên tắc “không bằng chứng → không kết luận”. | **Báo cáo kết quả so sánh, trích dẫn** |
| **9** | UI bản 1 (upload, xem song song, kết quả theo mục). | **Báo cáo chatbot** |
| **10** | Xây dựng tập dữ liệu + baseline; chạy đánh giá vòng 1. | **Báo cáo bộ dữ liệu** |
| **11** | Cải tiến chất lượng (chunking/retrieval/prompt), giảm bịa/hallucination. | **Báo cáo đánh giá mô hình của nhóm** |
| **12** | Hoàn thiện báo cáo & demo. | **Quyển báo cáo & Slide demo** |

## 8. Điểm số

* Cho 2 văn bản tiếng Việt, nhóm nào so sánh, phát hiện sai khác **chính xác hơn** sẽ đạt điểm cao hơn.