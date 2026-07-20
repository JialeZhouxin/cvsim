"""Single-mode Wigner (ħ=1, xxpp): Gaussian closed form + Bosonic sum.

Vacuum V=I/2: W(0,0)=1/π.
Complex mean: envelope × exp(i δᵀ V⁻¹ s), s=Im(r̄) — note 04 §Bosonic Wigner.
"""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.state import BosonicState
from cvsim.gaussian.state import GaussianState


def wigner_point_gaussian(
    V: np.ndarray, rbar: np.ndarray, x: float, p: float
) -> complex:
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


def wigner_grid(
    state: GaussianState | BosonicState,
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
        fn = lambda x, p: wigner_gaussian(state, x, p)
    elif isinstance(state, BosonicState):
        fn = lambda x, p: wigner_bosonic(state, x, p)
    else:
        raise TypeError("state must be GaussianState or BosonicState")
    W = np.empty_like(X, dtype=float)
    for i in range(n):
        for j in range(n):
            W[i, j] = fn(float(X[i, j]), float(P[i, j]))
    return X, P, W
