"""Bosonic channels: per-component V ← X V Xᵀ + Y, r̄ ← X r̄; w fixed."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.state import BosonicState, Component


def _loss_XY(
    nmode: int, T: float, mode: int | None, nbar: float
) -> tuple[np.ndarray, np.ndarray]:
    """X, Y same as Gaussian loss (ħ=1)."""
    modes = range(nmode) if mode is None else (mode,)
    X = np.eye(2 * nmode, dtype=float)
    Y = np.zeros((2 * nmode, 2 * nmode), dtype=float)
    sT = np.sqrt(T)
    y = (1.0 - T) * (nbar + 0.5)
    for i in modes:
        X[i, i] = sT
        X[nmode + i, nmode + i] = sT
        Y[i, i] = y
        Y[nmode + i, nmode + i] = y
    return X, Y


def loss(
    state: BosonicState,
    T: float,
    mode: int | None = None,
    nbar: float = 0.0,
) -> BosonicState:
    """Photon loss on every component; weights unchanged.

    mode=None: same T on all modes; else single mode.
    nbar=0 → pure loss (legacy).
    """
    if not 0.0 <= T <= 1.0:
        raise ValueError(f"T must be in [0,1], got {T}")
    if nbar < 0.0:
        raise ValueError(f"nbar must be >= 0, got {nbar}")
    m = state.nmode
    if mode is not None and not 0 <= mode < m:
        raise IndexError(f"mode {mode} out of range for nmode={m}")

    X, Y = _loss_XY(m, T, mode, nbar)
    out: list[Component] = []
    for c in state.components:
        V = X @ c.V @ X.T + Y
        V = 0.5 * (V + V.T)
        rbar = X @ c.rbar
        out.append(Component(V=V, rbar=rbar, w=c.w))
    return BosonicState(components=out)
