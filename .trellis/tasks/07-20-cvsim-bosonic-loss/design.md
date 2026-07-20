# Design · Bosonic loss

## Formula

每组件独立（ħ=1, `V_vac=I/2`）：

\[
V_k' = X V_k X^{\mathsf T}+Y,\qquad \bar r_k' = X\bar r_k,\qquad w_k'=w_k
\]

`X,Y` 构造同 `cvsim.gaussian.channels.loss`（可抽共享 helper，或复制 15 行——优先 **复制/私有 `_xy`** 避免跨包纠缠；若一行 import 内部构建函数更短则用）。

## Files

```text
cvsim/bosonic/channels.py   # NEW loss
cvsim/bosonic/__init__.py
tests/test_bosonic_loss.py
quality + README 一行
```

## Trade-off

| 选择 | 原因 |
|------|------|
| w 不变 | 高斯 CPTP 作用对角混合表示 |
| 不合并组件 | YAGNI |
