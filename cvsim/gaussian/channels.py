"""Gaussian channels: V ← X V Xᵀ + Y, r̄ ← X r̄."""

from __future__ import annotations

import numpy as np

from cvsim.gaussian.state import GaussianState


def loss(
    state: GaussianState,
    T: float,
    mode: int | None = None,
    nbar: float = 0.0,
) -> GaussianState:
    """Photon loss with transmissivity T (ħ=1).

    mode=None: same T on all modes; else single mode.
    X=√T on acted quads,
    Y=(1-T)(nbar+1/2) on those diagonals.
    nbar=0 → pure loss into vacuum (legacy).
    """
    if not 0.0 <= T <= 1.0:
        raise ValueError(f"T must be in [0,1], got {T}")
    if nbar < 0.0:
        raise ValueError(f"nbar must be >= 0, got {nbar}")
    m = state.nmode
    if mode is not None and not 0 <= mode < m:
        raise IndexError(f"mode {mode} out of range for nmode={m}")

    modes = range(m) if mode is None else (mode,)
    X = np.eye(2 * m, dtype=float)
    Y = np.zeros((2 * m, 2 * m), dtype=float)
    sT = np.sqrt(T)
    y = (1.0 - T) * (nbar + 0.5)
    for i in modes:
        X[i, i] = sT
        X[m + i, m + i] = sT
        Y[i, i] = y
        Y[m + i, m + i] = y

    V = X @ state.V @ X.T + Y
    rbar = X @ state.rbar
    V = 0.5 * (V + V.T)
    return GaussianState(V=V, rbar=rbar)
