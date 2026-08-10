# PRD — phase4-ad-gates-advanced

## Goal
高级门双实现：`S_CZ` / `S_CX` / `U_beamsplitter` / `embed_U_2mode` / `S_from_unitary` / `S_mach_zehnder` 加 `backend=` 参数。

## Deliverables
- symplectic.py 6 函数 backend 化
- `tests/test_ad_gates_advanced.py`: backend 参数化；np 回归硬编码值；jax vs np 一致

## Acceptance
- 参数化测试全绿；592 全绿；jax 路径与 np 路径逐元素一致
