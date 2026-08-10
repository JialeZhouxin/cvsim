"""Backend protocol tests — `cvsim.backend` (Phase 4 F-AD, child 1).

Covers the numpy/jax dispatch core:
- `_get_xp` backend resolution (lazy jax import, x64 enforcement)
- `_set` / `_block` / `_allclose` np<->jnp equivalence helpers
- `require_jax` + error paths

JAX-dependent cases auto-skip when jax is not installed.
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim import backend as be

# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def test_backends_constant() -> None:
    assert be.BACKENDS == ("numpy", "jax")


def test_get_xp_numpy() -> None:
    assert be._get_xp("numpy") is np


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_get_xp_jax() -> None:
    import jax.numpy as jnp

    assert be._get_xp("jax") is jnp


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_x64_enforced_on_first_jax_use() -> None:
    # float64 is a hard contract (vision F-PERF); _get_xp must flip x64.
    be._get_xp("jax")
    import jax

    assert jax.config.jax_enable_x64 is True


def test_get_xp_unknown_backend() -> None:
    with pytest.raises(ValueError, match="Unknown backend"):
        be._get_xp("torch")


@pytest.mark.skipif(be.HAS_JAX, reason="jax installed; error path covered on jax-less env")
def test_get_xp_jax_missing_error() -> None:
    with pytest.raises(ImportError, match="jax"):
        be._get_xp("jax")


def test_require_jax_resolves_like_get_xp(backend: str) -> None:
    # require_jax must resolve exactly like _get_xp("jax")
    if backend == "jax":
        assert be.require_jax() is be._get_xp("jax")


# ---------------------------------------------------------------------------
# _set helper (np in-place vs jnp immutable .at)
# ---------------------------------------------------------------------------


def test_set_numpy_inplace(backend: str) -> None:
    if backend != "numpy":
        pytest.skip("numpy-specific in-place semantics")
    a = np.zeros(4)
    r = be._set(np, a, (1,), 2.0)
    assert r is a
    assert a[1] == 2.0


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_set_jax_immutable() -> None:
    import jax.numpy as jnp

    a = jnp.zeros(4)
    r = be._set(jnp, a, (1,), 2.0)
    assert a[1] == 0.0  # original untouched
    assert r[1] == 2.0


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_set_jax_2d_index() -> None:
    import jax.numpy as jnp

    a = jnp.eye(3)
    r = be._set(jnp, a, (1, 2), jnp.exp(-0.5))
    assert float(r[1, 2]) == pytest.approx(float(jnp.exp(-0.5)))
    assert float(r[0, 0]) == 1.0


# ---------------------------------------------------------------------------
# _block helper (np.block vs jnp nested concatenate)
# ---------------------------------------------------------------------------


def _mixed_blocks():
    return [
        [np.eye(2), np.zeros((2, 1))],
        [np.ones((1, 2)), np.full((1, 1), 3.0)],
    ]


def test_block_numpy_matches_np_block(backend: str) -> None:
    if backend != "numpy":
        pytest.skip("numpy-specific comparison")
    blocks = _mixed_blocks()
    assert np.array_equal(be._block(np, blocks), np.block(blocks))


@pytest.mark.skipif(not be.HAS_JAX, reason="jax not installed")
def test_block_jax_matches_numpy() -> None:
    import jax.numpy as jnp

    blocks = _mixed_blocks()
    got = np.asarray(be._block(jnp, blocks))
    np.testing.assert_array_equal(got, np.block(blocks))


# ---------------------------------------------------------------------------
# _allclose helper
# ---------------------------------------------------------------------------


def test_allclose_backend(backend: str) -> None:
    xp = be._get_xp(backend)
    a = np.eye(2)
    b = np.eye(2) * (1.0 + 1e-9)
    assert be._allclose(xp, a, b)  # default rtol=1e-5 → True
    assert not be._allclose(xp, a, b, atol=1e-12, rtol=0.0)  # strict → False
    assert be._allclose(xp, a, a, atol=0.0, rtol=0.0)  # exact → True
