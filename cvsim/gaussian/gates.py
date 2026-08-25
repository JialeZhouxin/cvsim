"""Gaussian gates via affine symplectic maps: V ← S V Sᵀ, r̄ ← S r̄ + d."""

from __future__ import annotations

import numpy as np

from cvsim.gaussian.state import GaussianState
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


def apply_symplectic(
    state: GaussianState,
    S: np.ndarray,
    d: np.ndarray | None = None,
    *,
    validate: bool = True,
) -> GaussianState:
    """Apply r ↦ S r + d to a Gaussian state. Returns new state.

    If validate=True (default), require S Ω Sᵀ = Ω (xxpp).
    Named library gates pass validate=False (generators are trusted).
    """
    from cvsim.symplectic import validate_symplectic

    S = np.asarray(S, dtype=float)
    m2 = 2 * state.nmode
    if S.shape != (m2, m2):
        raise ValueError(f"S shape {S.shape} incompatible with nmode={state.nmode}")
    if validate:
        validate_symplectic(S)
    if d is None:
        d = np.zeros(m2, dtype=float)
    else:
        d = np.asarray(d, dtype=float)
        if d.shape != (m2,):
            raise ValueError(f"d shape {d.shape} incompatible with nmode={state.nmode}")
    V = S @ state.V @ S.T
    # numerical hygiene: keep V symmetric
    V = 0.5 * (V + V.T)
    rbar = S @ state.rbar + d
    return GaussianState(V=V, rbar=rbar)


def squeeze(state: GaussianState, r: float, mode: int = 0, phi: float = 0.0) -> GaussianState:
    """Single-mode squeeze S(r, φ)=R(φ)S(r)R(-φ) in xxpp.

    ``phi`` is the squeezing angle (same convention as ``GaussianState.squeezed``).
    """
    n = state.nmode
    S_r = S_squeeze(n, r, mode)
    S = S_r if phi == 0.0 else S_phase(n, phi, mode) @ S_r @ S_phase(n, -phi, mode)
    return apply_symplectic(state, S, validate=False)


def displace(state: GaussianState, alpha: complex, mode: int = 0) -> GaussianState:
    """Single-mode displacement D(α)."""
    return apply_symplectic(
        state,
        np.eye(2 * state.nmode),
        d_displace(state.nmode, alpha, mode),
        validate=False,
    )


def phase(state: GaussianState, theta: float, mode: int = 0) -> GaussianState:
    """Single-mode phase rotation R(θ)."""
    return apply_symplectic(state, S_phase(state.nmode, theta, mode), validate=False)


def beamsplitter(
    state: GaussianState,
    mode1: int,
    mode2: int,
    theta: float,
    phi: float = 0.0,
) -> GaussianState:
    """Two-mode beam splitter BS(θ, φ)."""
    return apply_symplectic(
        state,
        S_beamsplitter(state.nmode, mode1, mode2, theta, phi),
        validate=False,
    )


def two_mode_squeeze(state: GaussianState, r: float, mode1: int, mode2: int) -> GaussianState:
    """Two-mode squeeze S₂(r) (real r)."""
    return apply_symplectic(
        state,
        S_two_mode_squeeze(state.nmode, r, mode1, mode2),
        validate=False,
    )


def cz(state: GaussianState, weight: float, mode1: int, mode2: int) -> GaussianState:
    """Controlled-Z: CZ = exp(i·weight·x̂₁·x̂₂).

    p₁ → p₁ + weight·x₂, p₂ → p₂ + weight·x₁.
    """
    return apply_symplectic(state, S_CZ(state.nmode, weight, mode1, mode2), validate=False)


def cx(state: GaussianState, weight: float, mode1: int, mode2: int) -> GaussianState:
    """Controlled-X: CX = exp(-i·weight·x̂₁·p̂₂).

    x₂ → x₂ + weight·x₁, p₁ → p₁ - weight·p₂.
    """
    return apply_symplectic(state, S_CX(state.nmode, weight, mode1, mode2), validate=False)


def fourier(state: GaussianState, mode: int = 0) -> GaussianState:
    """Fourier gate: phase rotation by π/2 on ``mode`` (â → iâ in our S_phase sign)."""
    return phase(state, 0.5 * np.pi, mode=mode)


def mach_zehnder(
    state: GaussianState,
    mode1: int,
    mode2: int,
    theta: float,
    phi: float = 0.0,
) -> GaussianState:
    """Mach–Zehnder: BS(θ) → phase(φ) on mode1 → BS(π/4).

    See ``S_mach_zehnder`` for the fixed decomposition.
    """
    return apply_symplectic(
        state,
        S_mach_zehnder(state.nmode, mode1, mode2, theta, phi),
        validate=False,
    )


def interferometer(
    state: GaussianState,
    U: np.ndarray,
    *,
    validate_u: bool = True,
) -> GaussianState:
    """Apply passive linear optics U (m×m unitary) to an m-mode Gaussian state.

    ``validate_u=True`` (default) rejects non-unitary U. Setting
    ``validate_u=False`` is a **trusted escape hatch only**: a non-unitary U
    yields a non-symplectic S and can silently break physicality. Do not use
    on untrusted input.
    """
    U = np.asarray(U, dtype=complex)
    if U.shape != (state.nmode, state.nmode):
        raise ValueError(f"U shape {U.shape} incompatible with nmode={state.nmode}")
    S = S_from_unitary(U, validate=validate_u)
    return apply_symplectic(state, S, validate=False)


# alias
apply_interferometer = interferometer


def apply_mesh(state: GaussianState, ops: list[tuple]) -> GaussianState:
    """Apply Reck/Clements mesh ops (from ``clements_decomposition``) in order."""
    from cvsim.symplectic import S_from_unitary, embed_U_2mode

    st = state
    m = st.nmode
    for op in ops:
        kind = op[0]
        if kind == "u2":
            _, i, j, U2 = op
            U = embed_U_2mode(m, i, j, U2)
            st = apply_symplectic(st, S_from_unitary(U, validate=False), validate=False)
        elif kind == "bs":
            _, i, j, theta, phi = op
            st = beamsplitter(st, i, j, theta, phi)
        elif kind == "phase":
            _, i, theta = op
            st = phase(st, theta, mode=i)
        else:
            raise ValueError(f"unknown mesh op {kind!r}")
    return st
