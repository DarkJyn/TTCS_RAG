# Báo cáo so sánh retrieval

- run_id: `20260331T153452Z`
- model_name: `BAAI/bge-m3`
- index_dir: `output_index`
- dataset: `eval_queries.template.jsonl`
- configs: `semantic_only, semantic_clause_boost, semantic_clause_filter`
- ks: `1, 3, 5`

## Tầng kết luận cuối (enforce: không bằng chứng thì không kết luận)

- evidence_top_k: `2`
- min_support_rate: `0.80`
- min_supported_queries: `1`

- `semantic_only`: gate_pass=`True` | supported/assessed=`3/3` | support_rate=`1.000`
- `semantic_clause_boost`: gate_pass=`True` | supported/assessed=`3/3` | support_rate=`1.000`
- `semantic_clause_filter`: gate_pass=`True` | supported/assessed=`3/3` | support_rate=`1.000`
- Kết luận cuối: chọn config `semantic_only`.

## Kết quả retrieval top-k (log để làm citation sau)

Mỗi kết quả gồm: `rank, score, chunk_id, heading, source_path, snippet`.

### Điều 5 công bố danh mục các phần mềm phổ biến gồm các nội dung nào?

- group: `dieu_cu_the`
- clause_signals: `{'dieu': '5', 'khoan': None}`

#### Config: `semantic_clause_boost`

- rank=1 score=0.7542 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::10` | heading=`Điều 5.` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 5. Công bố danh mục các phần mềm phổ biến 1. Phần mềm phổ biến là phần mềm đáp ứng các tiêu chí sau: a) Được nhiều bộ, cơ quan trung ương, địa phương có nhu cầu đầu tư, mua sắm, thuê dịch vụ công nghệ thông tin giống nhau về chức nă...
- rank=2 score=0.5729 | chunk_id=`van-ban_Xay-dung-Do-thi_Nghi-dinh-35-2026-ND-CP-huong-dan-Nghi-quyet-ve-phan-loai-do-thi-286990_aspx::23` | heading=`Điều 5 và Điều 7 của Nghị định` | source=`input_docs\van-ban_Xay-dung-Do-thi_Nghi-dinh-35-2026-ND-CP-huong-dan-Nghi-quyet-ve-phan-loai-do-thi-286990_aspx.txt`
  - snippet: Điều 5 và Điều 7 của Nghị định này . 3. Các hoạt động phát triển đô thị tăng trưởng xanh được triển khai và vận hành dựa trên ứng dụng công nghệ thông tin, chuyển đổi số và các hệ thống thông tin khác bảo đảm tích hợp, kết nối, chia sẻ v...
- rank=3 score=0.5530 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::24` | heading=`Điều 15. Mô tả` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 15. Mô tả yêu cầu kỹ thuật cần đáp ứng của phần mềm nội bộ 1. Các thông số chủ yếu: a) Các quy trình nghiệp vụ (tổ chức, vận hành của quy trình, sản phẩm của quá trình nghiệp vụ, các giao tác xử lý của quy trình nghiệp vụ); b) Các đ...
- evidence_status=`SUPPORTED` | supporting_hits=`1` | evidence_top_k=`2`
- final_conclusion: Đủ bằng chứng để kết luận. Citation chính: chunk_id=Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::10 | source=input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt
- top_evidence: rank=1 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::10` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`

#### Config: `semantic_clause_filter`

- rank=1 score=0.7542 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::10` | heading=`Điều 5.` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 5. Công bố danh mục các phần mềm phổ biến 1. Phần mềm phổ biến là phần mềm đáp ứng các tiêu chí sau: a) Được nhiều bộ, cơ quan trung ương, địa phương có nhu cầu đầu tư, mua sắm, thuê dịch vụ công nghệ thông tin giống nhau về chức nă...
- rank=2 score=0.5530 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::24` | heading=`Điều 15. Mô tả` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 15. Mô tả yêu cầu kỹ thuật cần đáp ứng của phần mềm nội bộ 1. Các thông số chủ yếu: a) Các quy trình nghiệp vụ (tổ chức, vận hành của quy trình, sản phẩm của quá trình nghiệp vụ, các giao tác xử lý của quy trình nghiệp vụ); b) Các đ...
- rank=3 score=0.5292 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::57` | heading=`khoản 5 Điều 3 của Nghị định này` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: này. Bộ, cơ quan trung ương, Ủy ban nhân dân cấp tỉnh có trách nhiệm kiểm tra, giám sát đơn vị sử dụng ngân sách trong việc triển khai nhiệm vụ bảo đảm tiết kiệm, hiệu quả, phòng ngừa xảy ra thất thoát, lãng phí, tiêu cực. Đơn vị sử dụng...
- evidence_status=`SUPPORTED` | supporting_hits=`1` | evidence_top_k=`2`
- final_conclusion: Đủ bằng chứng để kết luận. Citation chính: chunk_id=Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::10 | source=input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt
- top_evidence: rank=1 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::10` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`

#### Config: `semantic_only`

- rank=1 score=0.7542 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::10` | heading=`Điều 5.` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 5. Công bố danh mục các phần mềm phổ biến 1. Phần mềm phổ biến là phần mềm đáp ứng các tiêu chí sau: a) Được nhiều bộ, cơ quan trung ương, địa phương có nhu cầu đầu tư, mua sắm, thuê dịch vụ công nghệ thông tin giống nhau về chức nă...
- rank=2 score=0.5530 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::24` | heading=`Điều 15. Mô tả` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 15. Mô tả yêu cầu kỹ thuật cần đáp ứng của phần mềm nội bộ 1. Các thông số chủ yếu: a) Các quy trình nghiệp vụ (tổ chức, vận hành của quy trình, sản phẩm của quá trình nghiệp vụ, các giao tác xử lý của quy trình nghiệp vụ); b) Các đ...
- rank=3 score=0.5292 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::57` | heading=`khoản 5 Điều 3 của Nghị định này` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: này. Bộ, cơ quan trung ương, Ủy ban nhân dân cấp tỉnh có trách nhiệm kiểm tra, giám sát đơn vị sử dụng ngân sách trong việc triển khai nhiệm vụ bảo đảm tiết kiệm, hiệu quả, phòng ngừa xảy ra thất thoát, lãng phí, tiêu cực. Đơn vị sử dụng...
- evidence_status=`SUPPORTED` | supporting_hits=`1` | evidence_top_k=`2`
- final_conclusion: Đủ bằng chứng để kết luận. Citation chính: chunk_id=Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::10 | source=input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt
- top_evidence: rank=1 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::10` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`

### Khoản 1 Điều 8 quy định những giai đoạn nào trong trình tự đầu tư dự án?

- group: `khoan_va_dieu`
- clause_signals: `{'dieu': '8', 'khoan': '1'}`

#### Config: `semantic_clause_boost`

- rank=1 score=0.8001 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16` | heading=`Điều 8. Trình` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 8. Trình tự đầu tư dự án 1. Trình tự đầu tư dự án đầu tư ứng dụng công nghệ thông tin bao gồm các giai đoạn: a) Chuẩn bị đầu tư; b) Thực hiện đầu tư; c) Kết thúc đầu tư. 2. Các hoạt động trong giai đoạn thực hiện đầu tư và kết thúc ...
- rank=2 score=0.7175 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::83` | heading=`Điều 1.` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 1. Phê duyệt đầu tư dự án (Tên dự án). . . với các nội dung chủ yếu sau: Tên dự án; chủ đầu tư; tổ chức tư vấn lập báo cáo nghiên cứu khả thi hoặc báo cáo kinh tế - kỹ thuật (nếu có); mục tiêu, quy mô đầu tư / thuê dịch vụ công nghệ...
- rank=3 score=0.7134 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::59` | heading=`khoản 5 Điều 8 của Nghị định này.` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: khoản 5 Điều 8 của Nghị định này. a) Đơn vị sử dụng ngân sách (sau đây gọi là chủ đầu tư) tự thực hiện hoặc thuê tổ chức, cá nhân tổ chức khảo sát (nếu cần thiết) và lập báo cáo nghiên cứu khả thi hoặc báo cáo kinh tế - kỹ thuật; trình c...
- evidence_status=`SUPPORTED` | supporting_hits=`1` | evidence_top_k=`2`
- final_conclusion: Đủ bằng chứng để kết luận. Citation chính: chunk_id=Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16 | source=input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt
- top_evidence: rank=1 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`

#### Config: `semantic_clause_filter`

- rank=1 score=0.6801 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16` | heading=`Điều 8. Trình` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 8. Trình tự đầu tư dự án 1. Trình tự đầu tư dự án đầu tư ứng dụng công nghệ thông tin bao gồm các giai đoạn: a) Chuẩn bị đầu tư; b) Thực hiện đầu tư; c) Kết thúc đầu tư. 2. Các hoạt động trong giai đoạn thực hiện đầu tư và kết thúc ...
- rank=2 score=0.6003 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::2` | heading=`Điều 9 Luật Ban hành văn bản quy phạm pháp luật 2025` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Các hoạt động trong giai đoạn thực hiện đầu tư và kết thúc đầu tư có thể thực hiện tuần tự hoặc xen kẽ tùy theo điều kiện cụ thể của từng dự án và do cấp có thẩm quyền quyết định đầu tư xác định. (1) Trong giai đoạn chuẩn bị đầu tư, các ...
- rank=3 score=0.5975 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::83` | heading=`Điều 1.` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 1. Phê duyệt đầu tư dự án (Tên dự án). . . với các nội dung chủ yếu sau: Tên dự án; chủ đầu tư; tổ chức tư vấn lập báo cáo nghiên cứu khả thi hoặc báo cáo kinh tế - kỹ thuật (nếu có); mục tiêu, quy mô đầu tư / thuê dịch vụ công nghệ...
- evidence_status=`SUPPORTED` | supporting_hits=`1` | evidence_top_k=`2`
- final_conclusion: Đủ bằng chứng để kết luận. Citation chính: chunk_id=Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16 | source=input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt
- top_evidence: rank=1 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`

#### Config: `semantic_only`

- rank=1 score=0.6801 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16` | heading=`Điều 8. Trình` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 8. Trình tự đầu tư dự án 1. Trình tự đầu tư dự án đầu tư ứng dụng công nghệ thông tin bao gồm các giai đoạn: a) Chuẩn bị đầu tư; b) Thực hiện đầu tư; c) Kết thúc đầu tư. 2. Các hoạt động trong giai đoạn thực hiện đầu tư và kết thúc ...
- rank=2 score=0.6003 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::2` | heading=`Điều 9 Luật Ban hành văn bản quy phạm pháp luật 2025` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Các hoạt động trong giai đoạn thực hiện đầu tư và kết thúc đầu tư có thể thực hiện tuần tự hoặc xen kẽ tùy theo điều kiện cụ thể của từng dự án và do cấp có thẩm quyền quyết định đầu tư xác định. (1) Trong giai đoạn chuẩn bị đầu tư, các ...
- rank=3 score=0.5975 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::83` | heading=`Điều 1.` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 1. Phê duyệt đầu tư dự án (Tên dự án). . . với các nội dung chủ yếu sau: Tên dự án; chủ đầu tư; tổ chức tư vấn lập báo cáo nghiên cứu khả thi hoặc báo cáo kinh tế - kỹ thuật (nếu có); mục tiêu, quy mô đầu tư / thuê dịch vụ công nghệ...
- evidence_status=`SUPPORTED` | supporting_hits=`1` | evidence_top_k=`2`
- final_conclusion: Đủ bằng chứng để kết luận. Citation chính: chunk_id=Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16 | source=input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt
- top_evidence: rank=1 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`

### trình tự đầu tư dự án đầu tư ứng dụng công nghệ thông tin

- group: `ngu_nghia_rong`
- clause_signals: `{'dieu': None, 'khoan': None}`

#### Config: `semantic_clause_boost`

- rank=1 score=0.7710 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16` | heading=`Điều 8. Trình` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 8. Trình tự đầu tư dự án 1. Trình tự đầu tư dự án đầu tư ứng dụng công nghệ thông tin bao gồm các giai đoạn: a) Chuẩn bị đầu tư; b) Thực hiện đầu tư; c) Kết thúc đầu tư. 2. Các hoạt động trong giai đoạn thực hiện đầu tư và kết thúc ...
- rank=2 score=0.7640 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::14` | heading=`khoản 5 Điều 3 của Nghị định này` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: khoản 5 Điều 3 của Nghị định này (sau đây gọi là dự án mua sắm); c) Dự án thuê dịch vụ công nghệ thông tin. 2 . Dự án đầu tư ứng dụng công nghệ thông tin sử dụng vốn ngân sách nhà nước chi cho đầu tư công thực hiện theo quy định của Luật...
- rank=3 score=0.7138 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::12` | heading=`Điều 7. Quản lý dự án đầu tư ứng dụng công nghệ thông tin` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 7. Quản lý dự án đầu tư ứng dụng công nghệ thông tin 1. Dự án đầu tư ứng dụng công nghệ thông tin sử dụng vốn ngân sách nhà nước chi cho đầu tư công bao gồm: a) Dự án đầu tư hệ thống thông tin, phần cứng, phần mềm, cơ sở dữ liệu quy...
- evidence_status=`SUPPORTED` | supporting_hits=`1` | evidence_top_k=`2`
- final_conclusion: Đủ bằng chứng để kết luận. Citation chính: chunk_id=Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16 | source=input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt
- top_evidence: rank=1 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`

#### Config: `semantic_clause_filter`

- rank=1 score=0.7710 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16` | heading=`Điều 8. Trình` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 8. Trình tự đầu tư dự án 1. Trình tự đầu tư dự án đầu tư ứng dụng công nghệ thông tin bao gồm các giai đoạn: a) Chuẩn bị đầu tư; b) Thực hiện đầu tư; c) Kết thúc đầu tư. 2. Các hoạt động trong giai đoạn thực hiện đầu tư và kết thúc ...
- rank=2 score=0.7640 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::14` | heading=`khoản 5 Điều 3 của Nghị định này` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: khoản 5 Điều 3 của Nghị định này (sau đây gọi là dự án mua sắm); c) Dự án thuê dịch vụ công nghệ thông tin. 2 . Dự án đầu tư ứng dụng công nghệ thông tin sử dụng vốn ngân sách nhà nước chi cho đầu tư công thực hiện theo quy định của Luật...
- rank=3 score=0.7138 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::12` | heading=`Điều 7. Quản lý dự án đầu tư ứng dụng công nghệ thông tin` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 7. Quản lý dự án đầu tư ứng dụng công nghệ thông tin 1. Dự án đầu tư ứng dụng công nghệ thông tin sử dụng vốn ngân sách nhà nước chi cho đầu tư công bao gồm: a) Dự án đầu tư hệ thống thông tin, phần cứng, phần mềm, cơ sở dữ liệu quy...
- evidence_status=`SUPPORTED` | supporting_hits=`1` | evidence_top_k=`2`
- final_conclusion: Đủ bằng chứng để kết luận. Citation chính: chunk_id=Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16 | source=input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt
- top_evidence: rank=1 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`

#### Config: `semantic_only`

- rank=1 score=0.7710 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16` | heading=`Điều 8. Trình` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 8. Trình tự đầu tư dự án 1. Trình tự đầu tư dự án đầu tư ứng dụng công nghệ thông tin bao gồm các giai đoạn: a) Chuẩn bị đầu tư; b) Thực hiện đầu tư; c) Kết thúc đầu tư. 2. Các hoạt động trong giai đoạn thực hiện đầu tư và kết thúc ...
- rank=2 score=0.7640 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::14` | heading=`khoản 5 Điều 3 của Nghị định này` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: khoản 5 Điều 3 của Nghị định này (sau đây gọi là dự án mua sắm); c) Dự án thuê dịch vụ công nghệ thông tin. 2 . Dự án đầu tư ứng dụng công nghệ thông tin sử dụng vốn ngân sách nhà nước chi cho đầu tư công thực hiện theo quy định của Luật...
- rank=3 score=0.7138 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::12` | heading=`Điều 7. Quản lý dự án đầu tư ứng dụng công nghệ thông tin` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
  - snippet: Điều 7. Quản lý dự án đầu tư ứng dụng công nghệ thông tin 1. Dự án đầu tư ứng dụng công nghệ thông tin sử dụng vốn ngân sách nhà nước chi cho đầu tư công bao gồm: a) Dự án đầu tư hệ thống thông tin, phần cứng, phần mềm, cơ sở dữ liệu quy...
- evidence_status=`SUPPORTED` | supporting_hits=`1` | evidence_top_k=`2`
- final_conclusion: Đủ bằng chứng để kết luận. Citation chính: chunk_id=Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16 | source=input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt
- top_evidence: rank=1 | chunk_id=`Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin::16` | source=`input_docs\Ngh_nh_45_2026_N_-CP_s_a_i_Ngh_nh_73_2019_N_-CP_quy_nh_qu_n_l_u_t_ng_d_ng_c_ng_ngh_th_ng_tin.txt`
