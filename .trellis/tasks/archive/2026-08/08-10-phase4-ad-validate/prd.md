# PRD — phase4-ad-validate

## Goal
validate 系列 backend 化：`is_symplectic` / `validate_symplectic` / `is_unitary` / `validate_unitary`。

## Deliverables
- symplectic.py 4 函数加 `backend=`（`_allclose` 封装）
- `tests/test_ad_validate.py`: 已知 symplectic/非 symplectic 矩阵在 np/jax 下判定一致

## Acceptance
- 参数化测试全绿；592 全绿
