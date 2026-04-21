# Báo cáo đánh giá Comparison Engine

- run_id: `20260421T062605Z`
- ground_truth: `eval_comparison_gt.jsonl`
- pairs_dir: `test_pairs`
- num_pairs: `5`

## Kết quả tổng hợp

| Metric | Macro | Micro |
|---|---|---|
| Precision | 0.9000 | 0.8462 |
| Recall | 0.6667 | 0.6875 |
| F1 | 0.7333 | 0.7586 |

- Type accuracy: `0.9091`
- Totals: TP=`11` FP=`2` FN=`5`

## Kết quả theo cặp

### pair_01

- doc1: `pair_01_v1.txt` | doc2: `pair_01_v2.txt`
- P=1.0000 R=1.0000 F1=1.0000 TypeAcc=1.0000
- Stats: {'total': 26, 'added': 1, 'removed': 1, 'modified': 2, 'unchanged': 22}

### pair_02

- doc1: `pair_02_v1.txt` | doc2: `pair_02_v2.txt`
- P=1.0000 R=0.3333 F1=0.5000 TypeAcc=1.0000
- Stats: {'total': 15, 'added': 0, 'removed': 1, 'modified': 0, 'unchanged': 14}

### pair_03

- doc1: `pair_03_v1.txt` | doc2: `pair_03_v2.txt`
- P=1.0000 R=1.0000 F1=1.0000 TypeAcc=1.0000
- Stats: {'total': 21, 'added': 1, 'removed': 0, 'modified': 2, 'unchanged': 18}

### pair_04

- doc1: `pair_04_v1.txt` | doc2: `pair_04_v2.txt`
- P=0.5000 R=0.5000 F1=0.5000 TypeAcc=0.5000
- Stats: {'total': 18, 'added': 1, 'removed': 0, 'modified': 3, 'unchanged': 14}

### pair_05

- doc1: `pair_05_v1.txt` | doc2: `pair_05_v2.txt`
- P=1.0000 R=0.5000 F1=0.6667 TypeAcc=1.0000
- Stats: {'total': 31, 'added': 0, 'removed': 1, 'modified': 0, 'unchanged': 30}
