# PRD — phase4-ad-decompose

## Goal
decompose 系列加 `backend=` 参数但**仅 numpy**：`reck_decomposition` / `clements_decomposition` / `compose_unitary_mesh`。

## Deliverables
- symplectic.py 3 函数签名统一；jax → NotImplementedError（docstring + ponytail 注释）
- `tests/test_ad_decompose.py`: numpy 回归不变；jax raise 断言

## Acceptance
- numpy 路径行为与现状完全一致；`backend="jax"` raise NotImplementedError；592 全绿
