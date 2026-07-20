# Implement · GKP nn cross

## Preconditions

- [x] 用户批准
- [x] `task.py start`

## Checklist

1. [x] `gkp.py` cross nn
2. [x] tests
3. [x] quality / README
4. [x] pytest + UAT
5. [x] commit/finish

## Validation

```bash
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
```

## Risks

| 风险 | 缓解 |
|------|------|
| ε 小 ov 不可见 | AC 用 ε≈0.35 |
| 破坏 U7 | 默认 none |
