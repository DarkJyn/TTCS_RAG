# Báo cáo đánh giá Comparison Engine

- run_id: `20260413T183204Z`
- ground_truth: `eval_comparison_gt.jsonl`
- pairs_dir: `test_pairs`
- num_pairs: `5`

## Kết quả tổng hợp

| Metric | Macro | Micro |
|---|---|---|
| Precision | 0.8000 | 0.8571 |
| Recall | 0.3333 | 0.3750 |
| F1 | 0.4667 | 0.5217 |

- Type accuracy: `0.8333`
- Totals: TP=`6` FP=`1` FN=`10`

## Kết quả theo cặp

### pair_01

- doc1: `pair_01_v1.txt` | doc2: `pair_01_v2.txt`
- P=1.0000 R=0.5000 F1=0.6667 TypeAcc=1.0000
- Stats: {'total': 21, 'added': 1, 'removed': 1, 'modified': 0, 'unchanged': 19}

### pair_02

- doc1: `pair_02_v1.txt` | doc2: `pair_02_v2.txt`
- P=1.0000 R=0.3333 F1=0.5000 TypeAcc=1.0000
- Stats: {'total': 11, 'added': 0, 'removed': 1, 'modified': 0, 'unchanged': 10}

### pair_03

- doc1: `pair_03_v1.txt` | doc2: `pair_03_v2.txt`
- P=1.0000 R=0.3333 F1=0.5000 TypeAcc=1.0000
- Stats: {'total': 17, 'added': 1, 'removed': 0, 'modified': 0, 'unchanged': 16}

### pair_04

- doc1: `pair_04_v1.txt` | doc2: `pair_04_v2.txt`
- P=1.0000 R=0.5000 F1=0.6667 TypeAcc=0.5000
- Stats: {'total': 18, 'added': 1, 'removed': 0, 'modified': 1, 'unchanged': 16}

### pair_05

- doc1: `pair_05_v1.txt` | doc2: `pair_05_v2.txt`
- P=0.0000 R=0.0000 F1=0.0000 TypeAcc=0.0000
- Stats: {'total': 14, 'added': 0, 'removed': 0, 'modified': 1, 'unchanged': 13}
