"""Bosonic channels: per-component V ← X V Xᵀ + Y, r̄ ← X r̄; w fixed."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.state import BosonicState, Component


def _acted_modes(nmode: int, mode: int | None) -> list[int]:
    """Resolve acted modes: None → all, int → single (with bounds check)."""
    if mode is None:
        return list(range(nmode))
    if not 0 <= mode < nmode:
        raise IndexError(f"mode {mode} out of range for nmode={nmode}")
    return [mode]


def _channel_XY(
    nmode: int, modes: list[int], x_val: float, y_val: float
) -> tuple[np.ndarray, np.ndarray]:
    """X, Y diagonal on each acted mode's x/p pair (ħ=1, xxpp)."""
    X = np.eye(2 * nmode, dtype=float)
    Y = np.zeros((2 * nmode, 2 * nmode), dtype=float)
    for i in modes:
        X[i, i] = x_val
        X[nmode + i, nmode + i] = x_val
        Y[i, i] = y_val
        Y[nmode + i, nmode + i] = y_val
    return X, Y


def _apply_affine(state: BosonicState, X: np.ndarray, Y: np.ndarray) -> BosonicState:
    """Per-component V ← X V Xᵀ + Y (symmetrized), r̄ ← X r̄; w unchanged."""
    out: list[Component] = []
    for c in state.components:
        V = X @ c.V @ X.T + Y
        V = 0.5 * (V + V.T)
        rbar = X @ c.rbar
        out.append(Component(V=V, rbar=rbar, w=c.w))
    return BosonicState(components=out)


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
    X, Y = _channel_XY(m, _acted_modes(m, mode), np.sqrt(T), (1.0 - T) * (nbar + 0.5))
    return _apply_affine(state, X, Y)


def amplifier(
    state: BosonicState,
    G: float,
    mode: int | None = None,
    nbar: float = 0.0,
) -> BosonicState:
    """Phase-insensitive amplifier with gain G ≥ 1 on every component.

    Per acted mode: X = √G · I₂, Y = (G−1)(n̄_amp+½) · I₂.
    nbar=0 → quantum-limited amplifier. mode=None → all modes.
    """
    if not G >= 1.0:
        raise ValueError(f"G must be >= 1, got {G}")
    if nbar < 0.0:
        raise ValueError(f"nbar must be >= 0, got {nbar}")
    m = state.nmode
    X, Y = _channel_XY(m, _acted_modes(m, mode), np.sqrt(G), (G - 1.0) * (nbar + 0.5))
    return _apply_affine(state, X, Y)


def phase_noise(
    state: BosonicState,
    sigma: float,
    mode: int | None = None,
) -> BosonicState:
    """Phase diffusion via random-rotation average (Option B).

    Mode undergoes random phase rotation R(φ), φ ∼ N(0, σ²), averaged out:
    X = e^{−σ²/2} · I₂, Y = (1 − e^{−σ²}) · ½ · I₂ per acted mode.
    sigma=0 → identity. mode=None → all modes.
    """
    if sigma < 0.0:
        raise ValueError(f"sigma must be >= 0, got {sigma}")
    m = state.nmode
    damp = np.exp(-sigma * sigma / 2.0)
    X, Y = _channel_XY(m, _acted_modes(m, mode), damp, (1.0 - damp * damp) * 0.5)
    return _apply_affine(state, X, Y)
