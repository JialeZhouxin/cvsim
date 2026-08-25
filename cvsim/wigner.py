"""Single-mode Wigner (ħ=1, xxpp): Gaussian + Bosonic + Fock.

Vacuum V=I/2: W(0,0)=1/π.
Complex mean: envelope × exp(i δᵀ V⁻¹ s), s=Im(r̄) — note 04 §Bosonic Wigner.
Fock: number-basis kernel with associated Laguerre (Cahill–Glauber style).
"""

from __future__ import annotations

import numpy as np
from scipy.special import eval_genlaguerre, factorial

from cvsim.bosonic.state import BosonicState
from cvsim.fock.density import FockDensity
from cvsim.fock.state import FockState
from cvsim.gaussian.state import GaussianState


def wigner_point_gaussian(V: np.ndarray, rbar: np.ndarray, x: float, p: float) -> complex:
    """Single-mode Gaussian Wigner at (x,p). rbar may be complex."""
    V = np.asarray(V, dtype=float)
    rbar = np.asarray(rbar, dtype=complex).reshape(-1)
    if V.shape != (2, 2) or rbar.shape != (2,):
        raise ValueError("single-mode only: V (2,2), rbar (2,)")
    mu = rbar.real
    s = rbar.imag
    delta = np.array([x, p], dtype=float) - mu
    # pref = 1/(π √det(2V)); vacuum det(2V)=1 → 1/π
    det2v = float(np.linalg.det(2.0 * V))
    if det2v <= 0:
        raise ValueError(f"det(2V) must be > 0, got {det2v}")
    pref = 1.0 / (np.pi * np.sqrt(det2v))
    Vinv = np.linalg.inv(V)
    # (δ − i s)ᵀ V⁻¹ (δ − i s) = δV⁻¹δ − 2i δV⁻¹s − sV⁻¹s
    # exp(−½ · · ·) = exp(−½δV⁻¹δ) exp(+i δV⁻¹s) exp(+½ sV⁻¹s)
    quad = float(delta @ Vinv @ delta)
    s_boost = float(s @ Vinv @ s)
    env = pref * np.exp(-0.5 * quad + 0.5 * s_boost)
    phase = complex(np.exp(1j * float(delta @ Vinv @ s)))
    return env * phase


def wigner_gaussian(state: GaussianState, x: float, p: float) -> float:
    if state.nmode != 1:
        raise ValueError("wigner_gaussian: single-mode only")
    return float(wigner_point_gaussian(state.V, state.rbar, x, p).real)


def wigner_bosonic(state: BosonicState, x: float, p: float) -> float:
    if state.nmode != 1:
        raise ValueError("wigner_bosonic: single-mode only")
    total = 0.0 + 0.0j
    for c in state.components:
        total += c.w * wigner_point_gaussian(c.V, c.rbar, x, p)
    return float(total.real)


def _wigner_kernel_nm(n: int, m: int, x: float, p: float) -> complex:
    """⟨n|W|m⟩ kernel at (x,p); α=(x+ip)/√2, ħ=1."""
    alpha = (x + 1j * p) / np.sqrt(2.0)
    r2 = float(abs(alpha) ** 2)
    pref = np.exp(-2.0 * r2) / np.pi
    if n <= m:
        lag = eval_genlaguerre(n, m - n, 4.0 * r2)
        return (
            pref
            * ((-1.0) ** n)
            * np.sqrt(factorial(n) / factorial(m))
            * (2.0 * np.conj(alpha)) ** (m - n)
            * lag
        )
    lag = eval_genlaguerre(m, n - m, 4.0 * r2)
    return (
        pref * ((-1.0) ** m) * np.sqrt(factorial(m) / factorial(n)) * (2.0 * alpha) ** (n - m) * lag
    )


def wigner_fock(state: FockState | FockDensity, x: float, p: float) -> float:
    """Single-mode Fock pure or density Wigner at (x,p)."""
    if isinstance(state, FockState):
        if state.nmode != 1:
            raise ValueError("wigner_fock: single-mode only")
        rho = np.outer(state.amps, state.amps.conj())
    elif isinstance(state, FockDensity):
        if state.nmode != 1:
            raise ValueError("wigner_fock: single-mode only")
        rho = state.rho
    else:
        raise TypeError("state must be FockState or FockDensity")
    N = rho.shape[0]
    total = 0.0 + 0.0j
    for n in range(N):
        for m in range(N):
            rnm = rho[n, m]
            if abs(rnm) < 1e-16:
                continue
            total += rnm * _wigner_kernel_nm(n, m, x, p)
    return float(total.real)


def _wigner_grid_fock(rho: np.ndarray, X: np.ndarray, P: np.ndarray) -> np.ndarray:
    """Vectorized Wigner grid for Fock states (same kernel as
    :func:`wigner_fock`, evaluated over the full grid per (n, m) pair).

    The scalar path is an O(grid) loop of O(N²) kernels — ~0.5 s for
    n=64, N=10. Vectorizing over the grid first drops that to ~10 ms:
    ``eval_genlaguerre`` runs on the whole 64×64 array per pair.
    """
    N = rho.shape[0]
    alpha = (X + 1j * P) / np.sqrt(2.0)
    r2 = np.abs(alpha) ** 2
    pref = np.exp(-2.0 * r2) / np.pi
    W = np.zeros_like(X, dtype=float)
    for n in range(N):
        for m in range(N):
            rnm = rho[n, m]
            if abs(rnm) < 1e-16:
                continue
            if n <= m:
                lag = eval_genlaguerre(n, m - n, 4.0 * r2)
                kern = (
                    pref
                    * ((-1.0) ** n)
                    * np.sqrt(factorial(n) / factorial(m))
                    * (2.0 * np.conj(alpha)) ** (m - n)
                    * lag
                )
            else:
                lag = eval_genlaguerre(m, n - m, 4.0 * r2)
                kern = (
                    pref
                    * ((-1.0) ** m)
                    * np.sqrt(factorial(m) / factorial(n))
                    * (2.0 * alpha) ** (n - m)
                    * lag
                )
            W += (rnm * kern).real
    return W


def wigner_grid(
    state: GaussianState | BosonicState | FockState | FockDensity,
    lim: float = 5.0,
    n: int = 81,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (X, P, W) meshgrids, W real, shape (n,n)."""
    if n < 2:
        raise ValueError("n must be >= 2")
    xs = np.linspace(-lim, lim, n)
    ps = np.linspace(-lim, lim, n)
    X, P = np.meshgrid(xs, ps, indexing="xy")
    if isinstance(state, GaussianState):

        def fn(x, p):
            return wigner_gaussian(state, x, p)
    elif isinstance(state, BosonicState):

        def fn(x, p):
            return wigner_bosonic(state, x, p)
    elif isinstance(state, (FockState, FockDensity)):
        if state.nmode != 1:
            raise ValueError("wigner_grid: single-mode only")
        rho = (
            state.rho if isinstance(state, FockDensity) else np.outer(state.amps, state.amps.conj())
        )
        return X, P, _wigner_grid_fock(rho, X, P)
    else:
        raise TypeError("state must be GaussianState, BosonicState, FockState, or FockDensity")
    W = np.empty_like(X, dtype=float)
    for i in range(n):
        for j in range(n):
            W[i, j] = fn(float(X[i, j]), float(P[i, j]))
    return X, P, W
