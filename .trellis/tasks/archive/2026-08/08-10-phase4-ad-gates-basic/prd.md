# PRD — phase4-ad-gates-basic

## Goal
基础门双实现：`d_displace` / `S_squeeze` / `S_phase` / `S_beamsplitter` / `S_two_mode_squeeze` 加 `backend=` 参数。

## Deliverables
- symplectic.py 5 函数 backend 化（`_get_xp` + `_set`/`_block` helper）
- `tests/test_ad_gates_basic.py`: backend 参数化；np 路径 vs 硬编码已知值；jax vs np 数值一致；**梯度 vs 有限差分**（squeeze r / BS θ）

## Acceptance
- exit 1 主体：squeeze/BS 参数 jax.grad ≈ central difference（atol 1e-6）
- np 路径逐值等于现有实现（回归）；592 全绿
