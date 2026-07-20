"""Bosonic observables: weights + weighted moments (ħ=1, xxpp)."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.state import BosonicState, Component

_IM_TOL = 1e-8


def weight_sum(state: BosonicState) -> complex:
    """∑ w_k — should be 1 for a normalized density-operator decomposition."""
    return sum(c.w for c in state.components)


def _nmode(state: BosonicState) -> int:
    return state.nmode


def _check_mode(state: BosonicState, mode: int) -> int:
    m = _nmode(state)
    if not 0 <= mode < m:
        raise IndexError(f"mode {mode} out of range for nmode={m}")
    return m


def _homodyne_u(nmode: int, mode: int, phi: float) -> np.ndarray:
    u = np.zeros(2 * nmode, dtype=complex)
    u[mode] = np.cos(phi)
    u[nmode + mode] = np.sin(phi)
    return u


def _as_real(z: complex, name: str) -> float:
    if abs(z.imag) > _IM_TOL:
        raise ValueError(f"{name} has large imaginary part: {z}")
    return float(z.real)


def _mean_photon_component(c: Component, mode: int | None) -> complex:
    m = c.V.shape[0] // 2
    V, r = c.V, c.rbar

    def one(i: int) -> complex:
        xx = V[i, i] + r[i] ** 2
        pp = V[m + i, m + i] + r[m + i] ** 2
        return 0.5 * (xx + pp - 1.0)

    if mode is not None:
        if not 0 <= mode < m:
            raise IndexError(f"mode {mode} out of range for nmode={m}")
        return one(mode)
    return sum(one(i) for i in range(m))


def mean_photon(state: BosonicState, mode: int | None = None) -> float:
    """⟨n⟩ = ∑_k w_k ⟨n⟩_k (ħ=1). Returns real part."""
    if mode is not None:
        _check_mode(state, mode)
    total = 0.0 + 0.0j
    for c in state.components:
        total += c.w * _mean_photon_component(c, mode)
    return _as_real(total, "mean_photon")


def homodyne_mean(state: BosonicState, mode: int = 0, phi: float = 0.0) -> float:
    """Weighted edge mean ⟨x_φ⟩ = ∑ w_k (u·r̄_k)."""
    m = _check_mode(state, mode)
    u = _homodyne_u(m, mode, phi)
    total = 0.0 + 0.0j
    for c in state.components:
        total += c.w * (u @ c.rbar)
    return _as_real(total, "homodyne_mean")


def homodyne_var(state: BosonicState, mode: int = 0, phi: float = 0.0) -> float:
    """Weighted Var(x_φ) = ⟨x_φ²⟩ − μ² with ⟨x_φ²⟩ = ∑ w (uᵀVu + (u·r)²)."""
    m = _check_mode(state, mode)
    u = _homodyne_u(m, mode, phi)
    uf = u.real
    mu = 0.0 + 0.0j
    x2 = 0.0 + 0.0j
    for c in state.components:
        mean_k = complex(u @ c.rbar)
        var_k = float(uf @ c.V @ uf)
        mu += c.w * mean_k
        x2 += c.w * (var_k + mean_k**2)
    return _as_real(x2 - mu**2, "homodyne_var")
