# Implement · Homodyne sample

## Preconditions

- [x] 用户批准
- [x] `task.py start`

## Checklist

1. [x] G `homodyne_sample`
2. [x] B 实峰混合物（单组件对齐 G rng）
3. [x] 导出 + tests
4. [x] README / quality
5. [x] pytest 74 + UAT
6. [x] commit/finish

## Validation

```bash
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
```

## Risks

| 风险 | 缓解 |
|------|------|
| 统计 flaky | seed + 松容差 + 够大 N |
| cat 全落一侧 | 查 Re(w) 池 + N |
