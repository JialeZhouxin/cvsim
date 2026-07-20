# Implement · Wigner

## Preconditions

- [x] 用户批准
- [x] `task.py start`

## Checklist

1. [x] `wigner.py`（含 `+½ sᵀV⁻¹s` 复中心）
2. [x] grid + G/B
3. [x] tests（odd cat 负区）
4. [x] README + quality
5. [x] pytest + UAT
6. [x] commit/finish

## Validation

```bash
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
```

## Risks

| 风险 | 缓解 |
|------|------|
| 归一 1/π vs 2/π | 真空锁 1/π |
| 相位系数 | cat 负区测试 |
| 奇异 V | 条件后 G 可奇异；本切片网格用未测态 |
