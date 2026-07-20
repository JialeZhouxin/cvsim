# Implement · Fock loss A1

## Preconditions

- [x] 用户批准
- [x] `task.py start`

## Checklist

1. [x] `FockDensity`
2. [x] Kraus `loss`
3. [x] observables on ρ
4. [x] export + tests
5. [x] README / quality
6. [x] pytest 80 + UAT
7. [x] commit/finish

## Validation

```bash
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
```

## Risks

| 风险 | 缓解 |
|------|------|
| 截断误差 | 相干用够大 N；容差松 |
| Kraus 索引 | 单测 |1⟩ 闭式 |
