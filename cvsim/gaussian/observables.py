"""Gaussian observables (moments only; no sampling / conditional update)."""

from __future__ import annotations

import numpy as np

from cvsim.gaussian.state import GaussianState


def det_cov(state: GaussianState) -> float:
    """det(V). Pure single-mode Gaussian: 1/4."""
    return float(np.linalg.det(state.V))


def _check_mode(state: GaussianState, mode: int) -> int:
    m = state.nmode
    if not 0 <= mode < m:
        raise IndexError(f"mode {mode} out of range for nmode={m}")
    return m


def homodyne_mean(state: GaussianState, mode: int = 0, phi: float = 0.0) -> float:
    """Edge mean ⟨x_φ⟩, x_φ = x cosφ + p sinφ (xxpp, ħ=1)."""
    m = _check_mode(state, mode)
    c, s = np.cos(phi), np.sin(phi)
    r = state.rbar
    return float(c * r[mode] + s * r[m + mode])


def homodyne_var(state: GaussianState, mode: int = 0, phi: float = 0.0) -> float:
    """Edge variance Var(x_φ) = uᵀ V u (central; independent of r̄)."""
    m = _check_mode(state, mode)
    c, s = np.cos(phi), np.sin(phi)
    V = state.V
    i, p = mode, m + mode
    return float(c * c * V[i, i] + s * s * V[p, p] + 2.0 * s * c * V[i, p])


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
