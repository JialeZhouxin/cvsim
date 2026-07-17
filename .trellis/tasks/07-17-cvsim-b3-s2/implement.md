# Implement · B3 S₂

## Preconditions

- [x] 用户批准
- [x] `task.py start`
- [x] quality + symplectic

## Checklist

1. [x] `S_two_mode_squeeze`（EPR 型 xxpp）+ Ω
2. [x] G/B `two_mode_squeeze`
3. [x] `tests/test_b3_s2.py`
4. [x] README 门表
5. [x] quality-guidelines B3
6. [x] commit/finish

## Validation

```bash
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
```

## Risks

| 风险 | 缓解 |
|------|------|
| xxpp 嵌入下标错 | Ω + ⟨n⟩ 双锁 |
| 符号 Z 反号 | 相关符号用 ⟨n⟩ 与 det 不敏感部分 + 文献块对照 |
| 破 BS 回归 | 全量 test |

## Before start

- [x] D1–D3
- [x] design/implement
- [ ] jsonl
- [ ] 批准
