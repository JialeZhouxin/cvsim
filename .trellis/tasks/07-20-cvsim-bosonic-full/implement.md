# Implement · Bosonic 矩闭环

## Preconditions

- [x] 用户批准
- [x] `task.py start`
- [x] bosonic/* + gaussian 对照

## Checklist

1. [x] vacuum + from_gaussian
2. [x] mean_photon / homodyne_*
3. [x] tests/test_bosonic_full.py
4. [x] README + quality + directory-structure
5. [x] pytest 47 + UAT + m3
6. [x] commit/finish

## Validation

```bash
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
.venv\Scripts\python.exe -m cvsim.demos.m3_cat_weights
```

## Risks

| 风险 | 缓解 |
|------|------|
| cat ⟨n⟩ 忘 cross 二阶 | AC-B3 + 与单峰错公式对照 |
| Im 泄漏 | 测实部 + 小 tol |
| 破 cat 权重 | m3 / test_m3 必跑 |

## Before start

- [x] D1–D3
- [x] design/implement
- [ ] jsonl
- [ ] 批准
