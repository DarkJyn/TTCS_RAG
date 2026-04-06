# Kết luận tự động (Evidence Gate)

Nguyên tắc áp dụng: **không bằng chứng -> không kết luận**.

- semantic_only: gate_pass=True, supported/assessed=3/3, support_rate=1.000
- semantic_clause_boost: gate_pass=True, supported/assessed=3/3, support_rate=1.000
- semantic_clause_filter: gate_pass=True, supported/assessed=3/3, support_rate=1.000

Kết luận cuối: chọn cấu hình semantic_only.
Lý do: Ít nhất một cấu hình vượt ngưỡng bằng chứng; chọn cấu hình có support_rate cao nhất và metric retrieval tốt nhất.
