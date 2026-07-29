"""Gaussian gates via affine symplectic maps: V ← S V Sᵀ, r̄ ← S r̄ + d."""

from __future__ import annotations

import numpy as np

from cvsim.gaussian.state import GaussianState
from cvsim.symplectic import (
    S_beamsplitter,
    S_CX,
    S_CZ,
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


def squeeze(state: GaussianState, r: float, mode: int = 0) -> GaussianState:
    """Single-mode squeeze S(r) in xxpp."""
    return apply_symplectic(
        state, S_squeeze(state.nmode, r, mode), validate=False
    )


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
    return apply_symplectic(
        state, S_phase(state.nmode, theta, mode), validate=False
    )


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


def two_mode_squeeze(
    state: GaussianState, r: float, mode1: int, mode2: int
) -> GaussianState:
    """Two-mode squeeze S₂(r) (real r)."""
    return apply_symplectic(
        state,
        S_two_mode_squeeze(state.nmode, r, mode1, mode2),
        validate=False,
    )


def cz(
    state: GaussianState, weight: float, mode1: int, mode2: int
) -> GaussianState:
    """Controlled-Z: CZ = exp(i·weight·x̂₁·x̂₂).

    p₁ → p₁ + weight·x₂, p₂ → p₂ + weight·x₁.
    """
    return apply_symplectic(
        state, S_CZ(state.nmode, weight, mode1, mode2), validate=False
    )


def cx(
    state: GaussianState, weight: float, mode1: int, mode2: int
) -> GaussianState:
    """Controlled-X: CX = exp(-i·weight·x̂₁·p̂₂).

    x₂ → x₂ + weight·x₁, p₁ → p₁ - weight·p₂.
    """
    return apply_symplectic(
        state, S_CX(state.nmode, weight, mode1, mode2), validate=False
    )
