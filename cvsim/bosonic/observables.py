"""Bosonic observables: weights + weighted moments + condition Homodyne (ħ=1, xxpp)."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.state import (  # noqa: F401  (re-export: weight_sum moved to state.py, B1)
    BosonicState,
    Component,
    weight_sum,
)

_IM_TOL = 1e-8
_SIG_EPS = 1e-14


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


def homodyne_sample(
    state: BosonicState,
    mode: int = 0,
    phi: float = 0.0,
    *,
    rng: np.random.Generator | None = None,
    imag_tol: float = 1e-12,
) -> float:
    """Sample Homodyne from real-peak mixture (teaching).

    Pool components with real r̄ and Re(w)>0; pick k ∝ Re(w_k), then
    N(μ_k, σ_k²). Complex-mean (cross) terms excluded from the pool.
    Does not condition — call homodyne_condition separately.
    """
    if rng is None:
        rng = np.random.default_rng()
    m = _check_mode(state, mode)
    u = np.zeros(2 * m, dtype=float)
    u[mode] = np.cos(phi)
    u[m + mode] = np.sin(phi)

    pool: list[Component] = []
    weights: list[float] = []
    for c in state.components:
        if np.max(np.abs(c.rbar.imag)) > imag_tol:
            continue
        rw = float(c.w.real)
        if rw <= 0.0:
            continue
        pool.append(c)
        weights.append(rw)

    if not pool:
        raise ValueError("homodyne_sample: no real-mean positive-weight components")

    if len(pool) == 1:
        idx = 0
    else:
        p = np.asarray(weights, dtype=float)
        p = p / p.sum()
        idx = int(rng.choice(len(pool), p=p))
    c = pool[idx]
    mu = float(u @ c.rbar.real)
    var = float(u @ c.V @ u)
    if var <= _SIG_EPS:
        raise ValueError(f"homodyne variance too small: σ²={var}")
    return float(rng.normal(mu, np.sqrt(var)))


def homodyne_condition(
    state: BosonicState,
    mode: int,
    phi: float,
    outcome: float,
) -> BosonicState:
    """Ideal Homodyne condition on all components (complex-mean OK).

    Per component (same shape as Gaussian; r̄ may be complex):
      v=Vu, σ=uᵀVu, μ=u·r̄
      V'=V−vvᵀ/σ,  r̄'=r̄+v(outcome−μ)/σ
      w *= (2πσ)^{-1/2} exp(−(outcome−μ)²/(2σ))  # L may be complex
    Then renorm ∑w=1. Does not delete modes.

    Honesty: teaching closed-form extension; not full Generaldyne POVM.
    """
    m = _check_mode(state, mode)
    u = np.zeros(2 * m, dtype=float)
    u[mode] = np.cos(phi)
    u[m + mode] = np.sin(phi)

    kept: list[Component] = []
    raw_w: list[complex] = []

    for c in state.components:
        v = c.V @ u
        sigma = float(u @ v)
        if sigma <= _SIG_EPS:
            raise ValueError(f"homodyne variance too small: σ={sigma}")
        mu = complex(u @ c.rbar)
        L = (2.0 * np.pi * sigma) ** (-0.5) * np.exp(
            -0.5 * (outcome - mu) ** 2 / sigma
        )
        Vn = c.V - np.outer(v, v) / sigma
        Vn = 0.5 * (Vn + Vn.T)
        rn = c.rbar + v * ((outcome - mu) / sigma)
        kept.append(Component(V=Vn, rbar=rn, w=0.0 + 0.0j))
        raw_w.append(c.w * complex(L))

    s = sum(raw_w)
    if abs(s) < _SIG_EPS:
        raise ValueError("homodyne_condition: weight sum ~ 0 after likelihood")
    for comp, w in zip(kept, raw_w):
        comp.w = w / s
    return BosonicState(components=kept)


def homodyne_sample_and_condition(
    state: BosonicState,
    mode: int = 0,
    phi: float = 0.0,
    *,
    rng: np.random.Generator | None = None,
    imag_tol: float = 1e-12,
) -> tuple[float, BosonicState]:
    """Sample (real-peak mixture) then condition. Thin combo; no new physics."""
    o = homodyne_sample(state, mode, phi, rng=rng, imag_tol=imag_tol)
    return o, homodyne_condition(state, mode, phi, o)
