# Implement · B cond complex

## Preconditions

- [x] 用户批准
- [x] `task.py start`

## Checklist

1. [x] 全组件复仿射
2. [x] tests 改写
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
| 复 L 数值炸 | σ 下界；\|∑w\| 检查 |
| 与 G 漂移 | AC 单组件对齐 |
