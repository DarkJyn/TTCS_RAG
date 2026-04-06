# Báo cáo so sánh + citation (nghiệm thu)

- Thời điểm chạy: 2026-03-31
- Run ID: 20260331T153452Z
- Bộ dữ liệu đánh giá: eval_queries.template.jsonl (3 query)
- Mục tiêu chính: enforce nguyên tắc "không bằng chứng -> không kết luận" ở tầng kết luận cuối.

## 1. Tiêu chí nghiệm thu báo cáo

| Tiêu chí | Trạng thái | Bằng chứng |
|---|---|---|
| 100% kết luận đều có citation kèm theo | Đạt | Mọi query/config đều có evidence_status=SUPPORTED và final_conclusion có citation chính (chunk_id + source_path). |
| Không có câu kết luận nào thiếu evidence | Đạt | insufficient_queries=0 cho cả 3 config. |
| Có bảng so sánh định lượng giữa các cấu hình | Đạt | Có bảng metric Hit/Precision/Recall/MRR/nDCG tại mục 4. |
| Có ít nhất 3 case study minh họa đúng/sai | Đạt | Có 3 case study tại mục 6, mỗi case có ví dụ đúng và ví dụ sai/near-miss. |
| Có mục lỗi và hướng xử lý rõ ràng | Đạt | Có mục 7 (lỗi điển hình + hướng xử lý). |

Nguồn kiểm chứng tổng hợp:
- retrieval_runs/20260331T153452Z/summary_metrics.json
- retrieval_runs/20260331T153452Z/evidence_summary.json
- retrieval_runs/20260331T153452Z/retrieval_logs.jsonl
- retrieval_runs/20260331T153452Z/report.md

## 2. Mục tiêu và phạm vi

Báo cáo này đánh giá 3 cấu hình retrieval trên dữ liệu pháp lý tiếng Việt:
- semantic_only
- semantic_clause_boost
- semantic_clause_filter

Phạm vi:
- So sánh định lượng theo k = 1, 3, 5.
- Đánh giá tuân thủ nguyên tắc bằng chứng ở tầng kết luận cuối.
- Trích citation bắt buộc cho mọi kết luận.

## 3. Thiết lập so sánh (các cấu hình)

- Embedding model: BAAI/bge-m3
- Index: output_index (FAISS)
- Oversample: 250
- log_top_k: 5
- evidence_top_k: 2
- Ngưỡng gate: min_support_rate=0.8, min_supported_queries=1
- Clause boost: boost_dieu=0.12, boost_khoan=0.12
- strict_filter: false

## 4. Bộ truy vấn đánh giá

Từ eval_queries.template.jsonl:

1. Nhóm ngu_nghia_rong
- Query: "trình tự đầu tư dự án đầu tư ứng dụng công nghệ thông tin"
- relevant_chunk_ids: Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16

2. Nhóm khoan_va_dieu
- Query: "Khoản 1 Điều 8 quy định những giai đoạn nào trong trình tự đầu tư dự án?"
- relevant_chunk_ids: Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16

3. Nhóm dieu_cu_the
- Query: "Điều 5 công bố danh mục các phần mềm phổ biến gồm các nội dung nào?"
- relevant_chunk_ids: Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::10

## 5. Kết quả định lượng

### 5.1 So sánh overall giữa các cấu hình

| Config | Hit@1 | Precision@1 | Recall@1 | MRR@1 | nDCG@1 | Precision@3 | Recall@3 | MRR@5 | nDCG@5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| semantic_only | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3333 | 1.0000 | 1.0000 | 1.0000 |
| semantic_clause_boost | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3333 | 1.0000 | 1.0000 | 1.0000 |
| semantic_clause_filter | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.3333 | 1.0000 | 1.0000 | 1.0000 |

Nhận xét:
- Top-1 của cả 3 cấu hình đều đúng trên bộ 3 query hiện tại.
- Precision@3 thấp hơn do top-2/top-3 có nhiễu (không thuộc relevant_chunk_ids), dù top-1 vẫn đúng.

### 5.2 Kết quả evidence gate (tuân thủ nguyên tắc bằng chứng)

| Config | assessed_queries | supported_queries | insufficient_queries | support_rate | gate_pass |
|---|---:|---:|---:|---:|---|
| semantic_only | 3 | 3 | 0 | 1.000 | True |
| semantic_clause_boost | 3 | 3 | 0 | 1.000 | True |
| semantic_clause_filter | 3 | 3 | 0 | 1.000 | True |

Kết luận tầng gate:
- Vì có config vượt ngưỡng bằng chứng, hệ thống cho phép kết luận.
- Config được chọn tự động: semantic_only (đồng hạng support_rate và metric, chọn theo thứ tự tie-break trong script).

## 6. Phân tích citation và tuân thủ nguyên tắc bằng chứng

Chính sách áp dụng:
- Rule: no_evidence_no_conclusion
- Nếu không có bằng chứng hợp lệ trong evidence_top_k, kết luận phải ở trạng thái WITHHELD.

Kết quả chạy hiện tại:
- Tổng số cặp query-config: 9
- SUPPORTED: 9
- INSUFFICIENT_EVIDENCE: 0
- NO_GROUND_TRUTH: 0

Suy ra:
- 100% kết luận đều có citation hợp lệ.
- Không có câu kết luận nào thiếu evidence.

## 7. Case study minh họa đúng/sai (>= 3 case)

### Case 1 - Query theo Điều cụ thể (dieu_cu_the)

Query: "Điều 5 công bố danh mục các phần mềm phổ biến gồm các nội dung nào?"

Kết quả đúng (top-1):
- semantic_clause_boost, rank=1, score=0.7542
- Citation: chunk_id=Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::10
- Source: input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt
- Heading: Điều 5.

Ví dụ sai/near-miss:
- semantic_clause_boost, rank=2, score=0.5729
- Citation phản ví dụ: chunk_id=van-ban_Xay-dung-Do-thi_Nghi-dinh-35-2026-ND-CP-huong-dan-Nghi-quyet-ve-phan-loai-do-thi-286990_aspx::23
- Source: input_docs\van-ban_Xay-dung-Do-thi_Nghi-dinh-35-2026-ND-CP-huong-dan-Nghi-quyet-ve-phan-loai-do-thi-286990_aspx.txt
- Nhận định: nhiễu do trùng cụm "Điều 5" nhưng sai ngữ cảnh văn bản mục tiêu.

Kết luận case:
- Được phép kết luận vì có bằng chứng đúng ở top-1 (SUPPORTED).

### Case 2 - Query Khoản + Điều (khoan_va_dieu)

Query: "Khoản 1 Điều 8 quy định những giai đoạn nào trong trình tự đầu tư dự án?"

Kết quả đúng (top-1):
- semantic_clause_boost, rank=1, score=0.8001
- Citation: chunk_id=Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16
- Source: input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt
- Heading: Điều 8. Trình

Ví dụ sai/near-miss:
- semantic_clause_filter, rank=2, score=0.6003
- Citation phản ví dụ: chunk_id=Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::2
- Source: input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt
- Nhận định: nội dung có ngữ liệu gần (thực hiện đầu tư) nhưng không đúng chunk nhãn.

Kết luận case:
- Được phép kết luận vì citation đúng xuất hiện trong top_evidence và evidence_status=SUPPORTED.

### Case 3 - Query ngữ nghĩa rộng (ngu_nghia_rong)

Query: "trình tự đầu tư dự án đầu tư ứng dụng công nghệ thông tin"

Kết quả đúng (top-1):
- semantic_only, rank=1, score=0.7710
- Citation: chunk_id=Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16
- Source: input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt
- Heading: Điều 8. Trình

Ví dụ sai/near-miss:
- semantic_only, rank=2, score=0.7640
- Citation phản ví dụ: chunk_id=Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::14
- Source: input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt
- Nhận định: vẫn liên quan chủ đề chung nhưng không trùng nhãn relevant chính thức.

Kết luận case:
- Được phép kết luận do có bằng chứng đúng tại rank=1 trong cửa sổ evidence_top_k.

## 8. Phân tích lỗi điển hình và hướng xử lý

### Lỗi 1 - Nhiễu do trùng số Điều giữa văn bản khác miền

Biểu hiện:
- Case 1 có hit rank=2 từ văn bản đô thị (không phải văn bản mục tiêu CNTT).

Nguyên nhân:
- Trùng lexical marker "Điều 5" + ngữ liệu công nghệ thông tin.

Hướng xử lý:
- Bổ sung prior theo source/doc family khi truy vấn đã gắn ngữ cảnh văn bản đích.
- Thêm reranker semantic chuyên biệt pháp lý cho top-N.

### Lỗi 2 - Nhiễu trong các chunk mở đầu/mục lục/heading chung

Biểu hiện:
- Case 2 có hit không đúng nhãn ở rank=2/3 dù top-1 đúng.

Nguyên nhân:
- Các đoạn tổng quan/mục lục chứa cụm từ gần nghĩa và số điều khoản.

Hướng xử lý:
- Tăng quality filter ở bước ingest (loại khối menu/mục lục, boilerplate).
- Giảm điểm cho heading dạng tổng quát không phải nội dung điều khoản chính.

### Lỗi 3 - Bộ test nhỏ gây trần metric (khó phân tách config)

Biểu hiện:
- Cả 3 config đều đạt 1.0 cho các metric chính tại k=1 và mrr@5.

Nguyên nhân:
- Dataset template chỉ có 3 query, nhãn tương đối dễ.

Hướng xử lý:
- Mở rộng benchmark bằng eval_queries.auto.jsonl và tập nhãn thủ công khó hơn.
- Bổ sung query phủ nhiều văn bản và truy vấn mơ hồ đa nghĩa.

## 9. Kết luận và đề xuất cấu hình triển khai

Kết luận nghiệm thu:
- Báo cáo đã đạt đầy đủ 5 tiêu chí nghiệm thu bạn yêu cầu.
- Tầng kết luận cuối đã enforce đúng nguyên tắc "không bằng chứng -> không kết luận".

Đề xuất cấu hình triển khai hiện tại:
- Mặc định triển khai semantic_only để đơn giản, ổn định, chi phí thấp (do đồng hạng metric với 2 config còn lại trên bộ test hiện tại).
- Khi mở rộng tập query Khoản/Điều khó hơn, ưu tiên thử semantic_clause_boost + reranker để cải thiện precision top-k.

Khuyến nghị vận hành:
- Giữ evidence gate ở production để tự động WITHHELD khi thiếu bằng chứng.
- Mọi câu kết luận hiển thị cho người dùng phải kèm citation bắt buộc: chunk_id + source_path + snippet.
