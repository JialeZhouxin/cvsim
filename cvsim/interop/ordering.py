"""Quadrature ordering: xxpp <-> xpxp (vision §8, interop.ordering).

Project convention (cvsim/conventions.py): ``QUAD_ORDER = "xxpp"``, ħ = 1,
vector (x_1..x_m, p_1..p_m). External tools (Strawberry Fields, The Walrus
pre-0.22, Piquasso) often use xpxp: (x_1, p_1, ..., x_m, p_m).

Pure permutation — no hbar rescaling (SF defaults ħ=2 → V_sf = 2·V_ours;
caller's responsibility, see docs/sf-roundtrip.md). Core never switches to
external ordering "to make tests easier" (vision §8 rule).
"""

from __future__ import annotations

import numpy as np


def _perm(m: int) -> np.ndarray:
    """xxpp index -> xpxp index: out[2k] = k, out[2k+1] = m + k."""
    perm = np.empty(2 * m, dtype=np.intp)
    perm[0::2] = np.arange(m)
    perm[1::2] = np.arange(m) + m
    return perm


def _check(V: np.ndarray, rbar: np.ndarray) -> int:
    V = np.asarray(V, dtype=float)
    n = V.shape[0]
    if V.ndim != 2 or V.shape != (n, n) or n == 0 or n % 2 != 0:
        raise ValueError(f"V must be 2m x 2m even-dim square, got shape {V.shape}")
    if not np.allclose(V, V.T):
        raise ValueError("V must be symmetric")
    rbar = np.asarray(rbar, dtype=float)
    if rbar.shape != (n,):
        raise ValueError(f"rbar must have shape ({n},), got {rbar.shape}")
    return int(n // 2)


def to_xpxp(V: np.ndarray, rbar: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert (V, rbar) from xxpp to xpxp ordering. Returns copies."""
    m = _check(V, rbar)
    p = _perm(m)
    return V[p][:, p], rbar[p]


def from_xpxp(V: np.ndarray, rbar: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert (V, rbar) from xpxp to xxpp ordering. Returns copies."""
    m = _check(V, rbar)
    p = np.argsort(_perm(m))
    return V[p][:, p], rbar[p]
