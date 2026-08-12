# Backend Interface (Phase 4 F-AD)

> Dual-backend protocol for `cvsim`: numpy default, JAX optional. Landed 2026-08-10 (Phase 4 close, vision v0.3.0).

---

## Rules

| Rule | Detail |
|------|--------|
| **One jax-aware point** | `cvsim/backend.py` only: `_get_xp(backend)` / `require_jax()` / `_set` / `_block` / `_allclose`. Lazy `import jax` + x64 enabled on first use. Never import jax elsewhere. |
| **Keyword `*, backend="numpy"`** | All 19 `cvsim/symplectic.py` functions take `backend=` keyword. No global state (方案 1: explicit param). |
| **numpy default = zero regression** | Default path must be value-identical to pre-backend code. 592-test suite is the guard. |
| **jnp immutability** | JAX arrays immutable: use `.at[idx].set(...)` (`_set`), never `arr[i] = x`. |
| **no `np.block` on jax** | jax has no `np.block`; nested `jnp.concatenate` via `_block` helper. |
| **GaussianState stays numpy** | JAX path uses bare jnp arrays only; no dual-backend state class (locked Q: no GaussianState(jax)). |
| **decompose trio numpy-only** | `reck_decomposition` / `clements_decomposition` / `compose_unitary_mesh`: `backend="jax"` → `NotImplementedError` (docstring + ponytail: mesh AD not implemented). |

## Module placement (ADR-0001)

`cvsim.gaussian` / `cvsim.fock` / `cvsim.bosonic` rep packages import **only** `cvsim.conventions` + `cvsim.symplectic` (allowlist, enforced by `tests/test_architecture.py` AST scan). Anything needing `cvsim.backend` or other cvsim modules lives **top-level**:

- `cvsim/backend.py` — backend protocol
- `cvsim/ad.py` — differentiable chain (`apply_gaussian`, `log_neg_loss`; jnp mirror of `cvsim/gaussian/analyse.py` formulas, cross-linked comments)
- `cvsim/fock_ad.py` — Fock differentiable chain (`squeeze_u`/`bs_u`/`kerr_diag`/`cat_fidelity`/`bs_overlap`; numpy path reuses `cvsim/fock/gates.py` + `channels._kraus_ops` as a constant tensor + einsum `'kam,mn,kbn->ab'`; jax path is the jnp mirror, Phase F4)

## Test doctrine

- `tests/conftest.py` `backends` fixture: `"numpy"` + `pytest.param("jax", marks=skipif(no jax))`.
- New API tests parametrized over backends (exit 2); gradient tests vs central finite difference (exit 1).
- jax-less env: all jax cases skip; numpy-only still green (CI without `[jax]`).

## Physics notes (objective notebook)

- Under loss, TMSV `E_N(r)` **saturates** — no interior optimum; raw "max E_N under loss" pushes r→∞.
- Interior optimum requires a cost: energy penalty `E_N − λ·2sinh²r` (notebook 05). Reference optimum = brute-force scan (no closed form).
- TMSV freeze: `E_N = 2r/ln2`, `dE_N/dr = 2/ln2` (gradient self-check).
