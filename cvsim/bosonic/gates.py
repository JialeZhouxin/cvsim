"""Bosonic gates: apply the same symplectic map to every component; weights fixed."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.state import BosonicState, Component
from cvsim.gaussian.symplectic import (
    S_beamsplitter,
    S_phase,
    S_squeeze,
    d_displace,
)


def _nmode(state: BosonicState) -> int:
    if not state.components:
        raise ValueError("empty BosonicState")
    return state.components[0].V.shape[0] // 2


def apply_symplectic(
    state: BosonicState, S: np.ndarray, d: np.ndarray | None = None
) -> BosonicState:
    """V_k ← S V_k Sᵀ, r̄_k ← S r̄_k + d, w_k unchanged."""
    S = np.asarray(S, dtype=float)
    m2 = S.shape[0]
    if d is None:
        d = np.zeros(m2, dtype=float)
    else:
        d = np.asarray(d, dtype=float)
    out: list[Component] = []
    for c in state.components:
        V = S @ c.V @ S.T
        rbar = S @ c.rbar + d
        out.append(Component(V=V, rbar=rbar, w=c.w))
    return BosonicState(components=out)


def squeeze(state: BosonicState, r: float, mode: int = 0) -> BosonicState:
    m = _nmode(state)
    return apply_symplectic(state, S_squeeze(m, r, mode))


def displace(state: BosonicState, alpha: complex, mode: int = 0) -> BosonicState:
    m = _nmode(state)
    return apply_symplectic(state, np.eye(2 * m), d_displace(m, alpha, mode))


def phase(state: BosonicState, theta: float, mode: int = 0) -> BosonicState:
    m = _nmode(state)
    return apply_symplectic(state, S_phase(m, theta, mode))


def beamsplitter(
    state: BosonicState,
    mode1: int,
    mode2: int,
    theta: float,
    phi: float = 0.0,
) -> BosonicState:
    m = _nmode(state)
    return apply_symplectic(state, S_beamsplitter(m, mode1, mode2, theta, phi))
