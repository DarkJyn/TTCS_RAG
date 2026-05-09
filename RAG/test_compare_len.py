import sys
import os
sys.path.append(r"d:\Dean'sCode\TTCS\RAG")
from compare_engine import compare_documents, summary_stats
from rag_pipeline import read_txt

from pathlib import Path
d1 = read_txt(Path(r"d:\Dean'sCode\TTCS\RAG\test_pairs\pair_03_v1.txt"))
d2 = read_txt(Path(r"d:\Dean'sCode\TTCS\RAG\test_pairs\pair_03_v2.txt"))
diffs = compare_documents(d1, d2)
changed = [d.to_dict() for d in diffs if d.diff_type.value != 'unchanged']
print('Num changed:', len(changed))
ctx = ''
for d in changed[:15]:
    ctx += f"- {d['diff_type']} at {d['heading']}:\n  Old: {len(d['old_text'])} chars\n  New: {len(d['new_text'])} chars\n"
print(ctx)
total_chars = sum(len(d['old_text']) + len(d['new_text']) for d in changed[:15])
print('Total context length if full text:', total_chars)
