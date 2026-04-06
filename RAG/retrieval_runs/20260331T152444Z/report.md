# Báo cáo so sánh retrieval

- run_id: `20260331T152444Z`
- model_name: `BAAI/bge-m3`
- index_dir: `output_index`
- dataset: `eval_queries.template.jsonl`
- configs: `semantic_only, semantic_clause_boost, semantic_clause_filter`

## Tầng kết luận cuối (enforce: không bằng chứng thì không kết luận)

- evidence_top_k: `2`
- min_support_rate: `0.80`
- min_supported_queries: `1`

- `semantic_only`: gate_pass=`True` | supported/assessed=`1/1` | support_rate=`1.000`
- `semantic_clause_boost`: gate_pass=`True` | supported/assessed=`1/1` | support_rate=`1.000`
- `semantic_clause_filter`: gate_pass=`True` | supported/assessed=`1/1` | support_rate=`1.000`
- Kết luận cuối: chọn config `semantic_only`.

## Kết quả retrieval top-k (log để làm citation sau)

Mỗi kết quả gồm: `rank, score, chunk_id, heading, source_path, snippet`.

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
