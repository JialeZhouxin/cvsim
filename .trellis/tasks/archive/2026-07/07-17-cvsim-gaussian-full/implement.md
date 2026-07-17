# Implement · Gaussian 全流程

## Preconditions

- [x] 用户批准
- [x] `task.py start`
- [x] observables / 笔记 02

## Checklist

### G1

1. [x] `homodyne_condition`
2. [x] `tests/test_g1_homodyne_condition.py`
3. [x] G1 绿

### G2

4. [x] `channels.loss`
5. [x] `tests/test_g2_loss.py`
6. [x] README + quality + directory-structure
7. [x] pytest 37 + UAT

### 收尾

8. [x] commit / finish-work

## Validation

```bash
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
```

## Risks

| 风险 | 缓解 |
|------|------|
| 条件公式符号 | 用边缘 mean/var 交叉验 |
| `Y` 系数错 ħ | T=0→真空 锁死 |
| 奇异 V 后 det | 不强制 det 测 |

## Before start

- [x] D1–D3
- [x] design/implement
- [ ] jsonl
- [ ] 批准
