# Implement · B2 Homodyne

## Preconditions

- [x] 用户批准 prd/design/implement
- [x] `task.py start`
- [x] backend quality / directory

## Ordered checklist

### 1. API

1. [x] `homodyne_mean` / `homodyne_var`
2. [x] `__init__.py` export

### 2. Tests

1. [x] `tests/test_b2_homodyne.py`
2. [x] 全量 pytest 回归

### 3. Docs / finish

1. [x] `cvsim/README.md` Homodyne
2. [x] update-spec + commit + finish-work

## Validation

```bash
.venv\Scripts\python.exe -m pytest tests -q
```

## Risks

| 风险 | 缓解 |
|------|------|
| φ 定义 sin/cos 反 | 挤态 x/p 方差对调可测 |
| mean 含 √2 错 | D(α) AC-H3 锁 |
| 把二阶矩当中心方差 | 实现只用 V，不加 r̄² |

## Before start

- [x] PRD 收敛
- [x] design/implement
- [ ] jsonl
- [ ] 用户批准
