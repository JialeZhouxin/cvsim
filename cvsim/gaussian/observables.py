"""Gaussian observables and ideal Homodyne conditional update."""

from __future__ import annotations

import numpy as np

from cvsim.gaussian.state import GaussianState

_EPS = 1e-14


def det_cov(state: GaussianState) -> float:
    """det(V). Pure single-mode Gaussian: 1/4."""
    return float(np.linalg.det(state.V))


def _check_mode(state: GaussianState, mode: int) -> int:
    m = state.nmode
    if not 0 <= mode < m:
        raise IndexError(f"mode {mode} out of range for nmode={m}")
    return m


def _homodyne_u(nmode: int, mode: int, phi: float) -> np.ndarray:
    u = np.zeros(2 * nmode, dtype=float)
    u[mode] = np.cos(phi)
    u[nmode + mode] = np.sin(phi)
    return u


def homodyne_mean(state: GaussianState, mode: int = 0, phi: float = 0.0) -> float:
    """Edge mean ⟨x_φ⟩, x_φ = x cosφ + p sinφ (xxpp, ħ=1)."""
    m = _check_mode(state, mode)
    u = _homodyne_u(m, mode, phi)
    return float(u @ state.rbar)


def homodyne_var(state: GaussianState, mode: int = 0, phi: float = 0.0) -> float:
    """Edge variance Var(x_φ) = uᵀ V u (central; independent of r̄)."""
    m = _check_mode(state, mode)
    u = _homodyne_u(m, mode, phi)
    return float(u @ state.V @ u)


def homodyne_condition(
    state: GaussianState,
    mode: int,
    phi: float,
    outcome: float,
) -> GaussianState:
    """Ideal Homodyne condition (no mode delete; V singular on u).

    V' = V - vvᵀ/σ,  r̄' = r̄ + v (outcome-μ)/σ,  v=Vu, σ=uᵀVu, μ=u·r̄.
    """
    m = _check_mode(state, mode)
    u = _homodyne_u(m, mode, phi)
    V = state.V
    r = state.rbar
    v = V @ u
    sigma = float(u @ v)
    if sigma <= _EPS:
        raise ValueError(f"homodyne variance too small: σ={sigma}")
    mu = float(u @ r)
    Vn = V - np.outer(v, v) / sigma
    rn = r + v * ((outcome - mu) / sigma)
    # symmetrize float noise
    Vn = 0.5 * (Vn + Vn.T)
    return GaussianState(V=Vn, rbar=rn)


def mean_photon(state: GaussianState, mode: int | None = None) -> float:
    """Mean photon number ⟨n⟩.

    ħ=1, x=(a+a†)/√2, p=(a-a†)/(i√2):
      ⟨n_i⟩ = ½(⟨x_i²⟩ + ⟨p_i²⟩ − 1)

    If mode is None, return sum over all modes.
    """
    m = state.nmode
    V, r = state.V, state.rbar

    def one(i: int) -> float:
        _check_mode(state, i)
        # ⟨x²⟩ = V_xx + ⟨x⟩², ⟨p²⟩ = V_pp + ⟨p⟩²
        xx = V[i, i] + r[i] ** 2
        pp = V[m + i, m + i] + r[m + i] ** 2
        return 0.5 * (xx + pp - 1.0)

    if mode is not None:
        return one(mode)
    return sum(one(i) for i in range(m))
