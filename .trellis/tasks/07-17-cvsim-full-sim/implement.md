# Implement · B1 门集

## Preconditions

- [x] 用户批准 prd/design/implement
- [x] `task.py start`
- [x] before-dev / backend quality 已读

## Ordered checklist

### 0. 共享辛矩阵 helper

1. [x] `cvsim/gaussian/symplectic.py`
2. [x] `tests/test_b1_symplectic.py`

### 1. Gaussian

1. [x] D/R/S/BS
2. [x] AC-G1/G2/G3

### 2. Fock

1. [x] D/R/S
2. [x] AC-F1/F2

### 3. Bosonic

1. [x] `bosonic/gates.py`
2. [x] AC-B1/B2

### 4. 回归与文档

1. [x] pytest 21 passed
2. [x] `cvsim/README.md` 门列表
3. [x] update-spec + commit + finish-work

## Validation

```bash
.venv\Scripts\python.exe -m pytest tests -q
python -m cvsim.demos.m1_gaussian_squeeze
python -m cvsim.demos.m2_fock_cutoff_scan
python -m cvsim.demos.m3_cat_weights
```

## Risks

| 风险 | 缓解 |
|------|------|
| BS 符号/序错误 | Ω 单测 + 50:50 光子数对称 |
| α↔(x,p) 系数错 | ⟨n⟩=|α|² 锁 |
| Bosonic 复 r̄ 被 float 砍 | dtype complex 保持 |
| 破坏 MVP squeeze | 回归 test_m1 |

## Before start

- [x] PRD 收敛
- [x] design/implement
- [ ] jsonl 真实条目
- [ ] 用户批准
