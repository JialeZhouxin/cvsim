"""Backend dispatch core — the only JAX-aware module in cvsim (Phase 4 F-AD).

Design (task 08-10-cvsim-phase4-ad design.md §2):
- ``numpy`` is the default and only mandatory backend.
- ``jax`` is optional (extra ``[jax]``), lazily imported — the core import
  path never touches JAX (vision: "No AD in core import path").
- JAX x64 is enforced on first use: cvsim physics contracts are float64
  (vision F-PERF); float32 breaks every atol=1e-8 assertion.
- np/jnp difference helpers live here so the 19 backend-ised symplectic
  functions never re-implement them: ``_set`` (np in-place vs jnp immutable
  ``.at``), ``_block`` (jnp has no ``np.block``), ``_allclose``.
"""

from __future__ import annotations

import importlib.util
from typing import Any

import numpy as np

BACKENDS = ("numpy", "jax")
"""Supported backend names."""

HAS_JAX = importlib.util.find_spec("jax") is not None
"""Whether the optional jax extra is importable (spec check, no import)."""

_XP_CACHE: dict[str, Any] = {}


def _get_xp(backend: str) -> Any:
    """Resolve ``backend`` to its array module (``np`` or ``jnp``).

    Raises:
        ValueError: unknown backend name.
        ImportError: ``jax`` requested but not installed (with install hint).
    """
    if backend == "numpy":
        return np
    if backend == "jax":
        if backend not in _XP_CACHE:
            _XP_CACHE[backend] = _load_jax()
        return _XP_CACHE[backend]
    raise ValueError(f"Unknown backend {backend!r}; expected one of {BACKENDS}")


def _load_jax() -> Any:
    """Lazy-import jax.numpy with x64 enabled (idempotent)."""
    try:
        import jax
        import jax.numpy as jnp
    except ImportError:
        raise ImportError(
            "jax not installed; run `pip install -e '.[jax]'` (or `pip install jax[cpu]`)"
        ) from None
    jax.config.update("jax_enable_x64", True)  # type: ignore[no-untyped-call]
    return jnp


def require_jax() -> Any:
    """Return ``jax.numpy`` or raise ImportError with install hint."""
    return _get_xp("jax")


def _set(xp: Any, arr: Any, idx: tuple[int, ...], val: Any) -> Any:
    """Set ``arr[idx] = val`` backend-agnostically.

    numpy arrays are mutable (in-place); jnp arrays are immutable (``.at``).
    """
    if xp is np:
        arr[idx] = val
        return arr
    return arr.at[idx].set(val)


def _block(xp: Any, blocks: Any) -> Any:
    """Assemble a block matrix, ``np.block`` for numpy; nested concatenate for jnp."""
    if xp is np:
        return np.block(blocks)
    rows = [xp.concatenate(row, axis=1) for row in blocks]
    return xp.concatenate(rows, axis=0)


def _allclose(xp: Any, a: Any, b: Any, *, atol: float = 1e-8, rtol: float = 1e-5) -> bool:
    """Allclose with numpy's default tolerance semantics, backend-agnostic."""
    if xp is np:
        return bool(np.allclose(a, b, atol=atol, rtol=rtol))
    return bool(xp.allclose(a, b, atol=atol, rtol=rtol))
