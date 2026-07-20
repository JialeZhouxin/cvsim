# Implement · Fock 全流程

## Preconditions

- [x] 用户批准
- [x] `task.py start`
- [x] fock/* + m2

## Checklist

1. [x] `FockState` 1\|2 模
2. [x] 单模门 `mode=`
3. [x] `kerr` + `beamsplitter`
4. [x] `pnrd_probs` + 多模 `mean_photon`
5. [x] `tests/test_fock_full.py`
6. [x] README + quality + directory-structure
7. [x] pytest 42 + UAT + m2
8. [x] commit/finish

## Validation

```bash
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
.venv\Scripts\python.exe -m cvsim.demos.m2_fock_cutoff_scan
```

## Risks

| 风险 | 缓解 |
|------|------|
| BS expm 截断 | cutoff 够 + AC 相对 ½ |
| 破坏单模 | 旧 test 必跑 |
| ravel 序错 | |10⟩ 专用断言 |

## Before start

- [x] D1–D3
- [x] design/implement
- [ ] jsonl
- [ ] 批准
