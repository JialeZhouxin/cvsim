# PRD — phase4-ad-protocol

## Goal
Backend 分发基建：`cvsim/backend.py`（唯一 JAX 感知点）+ pyproject `[jax]` extra + conftest `backends` fixture。

## Deliverables
- `cvsim/backend.py`: `BACKENDS` / `_get_xp(backend)`（lazy jax import + 首次启用 x64）/ `require_jax()` / `_set` / `_block` / `_allclose`
- pyproject: `[jax]` extra（`jax>=0.4`, `jaxlib`）
- `tests/conftest.py`: `backends` fixture（jax 未装 skip）
- `tests/test_backend.py`: helper 等价性（np vs jnp 基本操作）、x64 断言、错误路径

## Acceptance
- pytest 新测试绿；592 回归绿；无 jax 时装/不装都绿
- `_get_xp("jax")` 未装时 raise ImportError 带 `pip install -e ".[jax]"` 提示
