"""Bosonic gates: apply the same symplectic map to every component; weights fixed."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.state import BosonicState, Component
from cvsim.symplectic import (
    S_CX,
    S_CZ,
    S_beamsplitter,
    S_from_unitary,
    S_mach_zehnder,
    S_phase,
    S_squeeze,
    S_two_mode_squeeze,
    d_displace,
)


def _nmode(state: BosonicState) -> int:
    if not state.components:
        raise ValueError("empty BosonicState")
    return int(state.components[0].V.shape[0] // 2)


def apply_symplectic(
    state: BosonicState, S: np.ndarray, d: np.ndarray | None = None
) -> BosonicState:
    """V_k ← S V_k Sᵀ, r̄_k ← S r̄_k + d, w_k unchanged."""
    S = np.asarray(S, dtype=float)
    m2 = S.shape[0]
    d = np.zeros(m2, dtype=float) if d is None else np.asarray(d, dtype=float)
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


def two_mode_squeeze(state: BosonicState, r: float, mode1: int, mode2: int) -> BosonicState:
    m = _nmode(state)
    return apply_symplectic(state, S_two_mode_squeeze(m, r, mode1, mode2))


def fourier(state: BosonicState, mode: int = 0) -> BosonicState:
    """Fourier gate: phase rotation by π/2 on ``mode`` (â → iâ)."""
    return phase(state, 0.5 * np.pi, mode=mode)


def mach_zehnder(
    state: BosonicState,
    mode1: int,
    mode2: int,
    theta: float,
    phi: float = 0.0,
) -> BosonicState:
    """Mach–Zehnder: BS(θ) → phase(φ) on mode1 → BS(π/4)."""
    m = _nmode(state)
    return apply_symplectic(state, S_mach_zehnder(m, mode1, mode2, theta, phi))


def cz(state: BosonicState, weight: float, mode1: int, mode2: int) -> BosonicState:
    """Controlled-Z: CZ = exp(i·weight·x̂₁·x̂₂)."""
    m = _nmode(state)
    return apply_symplectic(state, S_CZ(m, weight, mode1, mode2))


def cx(state: BosonicState, weight: float, mode1: int, mode2: int) -> BosonicState:
    """Controlled-X: CX = exp(-i·weight·x̂₁·p̂₂)."""
    m = _nmode(state)
    return apply_symplectic(state, S_CX(m, weight, mode1, mode2))


def interferometer(state: BosonicState, U: np.ndarray, *, validate_u: bool = True) -> BosonicState:
    """Apply passive linear optics U (m×m unitary) to every component.

    ``validate_u=True`` (default) rejects non-unitary U. Setting
    ``validate_u=False`` is a **trusted escape hatch only**: a non-unitary U
    yields a non-symplectic S and can silently break physicality.
    """
    m = _nmode(state)
    U = np.asarray(U, dtype=complex)
    if U.shape != (m, m):
        raise ValueError(f"U shape {U.shape} incompatible with nmode={m}")
    S = S_from_unitary(U, validate=validate_u)
    return apply_symplectic(state, S)
