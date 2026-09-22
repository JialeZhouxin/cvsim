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
    return complex(env * phase)


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
    """⟨n|W|m⟩ kernel at (x,p); α=(x+ip)/√2, ħ=1.

    The two branches differ in which of α / ᾱ carries the (m−n)/(n−m) power:
    ``n ≤ m`` uses α, ``n > m`` uses ᾱ. They are **not** interchangeable —
    ``W(α) = W(−α)`` only holds for a real α, so swapping them is invisible on
    the imaginary axis but mirrors the distribution in p once ⟨p̂⟩ ≠ 0.
    """
    alpha = (x + 1j * p) / np.sqrt(2.0)
    r2 = float(abs(alpha) ** 2)
    pref = np.exp(-2.0 * r2) / np.pi
    if n <= m:
        lag = eval_genlaguerre(n, m - n, 4.0 * r2)
        return complex(
            pref
            * ((-1.0) ** n)
            * np.sqrt(factorial(n) / factorial(m))
            * (2.0 * alpha) ** (m - n)
            * lag
        )
    lag = eval_genlaguerre(m, n - m, 4.0 * r2)
    return complex(
        pref
        * ((-1.0) ** m)
        * np.sqrt(factorial(m) / factorial(n))
        * (2.0 * np.conj(alpha)) ** (n - m)
        * lag
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

    α / ᾱ must match :func:`_wigner_kernel_nm` branch-for-branch (see the
    docstring there): ``n ≤ m`` takes α, ``n > m`` takes ᾱ.
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
                    * (2.0 * alpha) ** (m - n)
                    * lag
                )
            else:
                lag = eval_genlaguerre(m, n - m, 4.0 * r2)
                kern = (
                    pref
                    * ((-1.0) ** m)
                    * np.sqrt(factorial(m) / factorial(n))
                    * (2.0 * np.conj(alpha)) ** (n - m)
                    * lag
                )
            W += (rnm * kern).real
    return W


def wigner_plane(
    V: np.ndarray,
    rbar: np.ndarray,
    A: np.ndarray,
    lim: float = 5.0,
    n: int = 81,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Two-quadrature plane Wigner grid (X, Y, W) for a Gaussian state.

    Generalises :func:`wigner_point_gaussian`: ``A`` picks two orthonormal-ish
    quadrature combinations out of the ``2m`` xxpp quadratures, so the plane
    can mix modes (``x_k − x_j``, EPR basis, ...) instead of being a single
    mode's ``(x, p)``. With ``A = [e_k, e_{m+k}]`` this is exactly the
    ``partial_trace(keep=[k]) + wigner_grid`` path.

    ``C = A V Aᵀ`` (2×2) is the sub-covariance; ``r̄`` may be complex, in which
    case the envelope carries the phase (same convention as
    :func:`wigner_point_gaussian`: ``exp(+i δᵀC⁻¹s)``, ``s = Im(A r̄)``).

    The quadratic form is evaluated with the ``(d @ Cinv) @ d`` association
    order — see the note in :func:`_wigner_grid_gaussian` for why bitwise
    agreement with the scalar path depends on it.

    Raises
    ------
    ValueError
        Bad shapes, ``n < 2``, ``lim <= 0``, or ``det(2C) <= 0`` (singular
        sub-covariance → no finite Wigner; callers report null rather than
        fabricating data, same contract as ``wigner_point_gaussian``).
    """
    V = np.asarray(V, dtype=float)
    rbar = np.asarray(rbar, dtype=complex).reshape(-1)
    A = np.asarray(A, dtype=float)
    if V.ndim != 2 or V.shape[0] != V.shape[1] or V.shape[0] % 2 != 0:
        raise ValueError(f"V must be (2m,2m), got {V.shape}")
    m2 = V.shape[0]
    if A.shape != (2, m2):
        raise ValueError(f"A must be (2, {m2}) to match V, got {A.shape}")
    if rbar.shape != (m2,):
        raise ValueError(f"rbar must be ({m2},) to match V, got {rbar.shape}")
    if n < 2:
        raise ValueError("n must be >= 2")
    if not np.isfinite(lim) or lim <= 0:
        raise ValueError("lim must be a positive number")

    C = A @ V @ A.T
    mu_full = A @ rbar
    mu = mu_full.real
    s = mu_full.imag
    det2c = float(np.linalg.det(2.0 * C))
    if det2c <= 0:
        raise ValueError(f"det(2C) must be > 0, got {det2c}")
    pref = 1.0 / (np.pi * np.sqrt(det2c))
    Cinv = np.linalg.inv(C)

    xs = np.linspace(-lim, lim, n)
    # Same convention as wigner_grid: first output varies along columns (axis 1),
    # second along rows (axis 0).
    X, Y = np.meshgrid(xs, xs, indexing="xy")
    # Association order matters bitwise: scalar path does ((d @ Vinv) @ d).
    D = np.stack([X - mu[0], Y - mu[1]], axis=-1)
    DV = np.einsum("...i,ij->...j", D, Cinv)
    q = np.einsum("...i,...i->...", DV, D)
    ph = np.einsum("...i,i->...", DV, s)
    s_boost = float(s @ Cinv @ s)
    W = (pref * np.exp(-0.5 * q + 0.5 * s_boost) * np.exp(1j * ph)).real
    return X, Y, np.asarray(W, dtype=float)


def _wigner_grid_gaussian(
    V: np.ndarray, rbar: np.ndarray, lim: float, n: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Single-mode Gaussian grid via :func:`wigner_plane` with ``A=[e_0,e_1]``.

    Exists so ``wigner_grid``'s Gaussian branch and ``wigner_plane`` share one
    einsum kernel (two copies would drift). The old scalar loop called
    ``wigner_gaussian`` per grid point — 233 ms at n=64; this is ~0.6 ms.
    """
    m = V.shape[0] // 2
    A = np.zeros((2, 2 * m))
    # single mode k=0 of the already-reduced state: A = [e_0, e_m]
    A[0, 0] = 1.0
    A[1, m] = 1.0
    return wigner_plane(V, rbar, A, lim=lim, n=n)


def wigner_grid(
    state: GaussianState | BosonicState | FockState | FockDensity,
    lim: float = 5.0,
    n: int = 81,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (X, P, W) meshgrids, W real, shape (n,n)."""
    if n < 2:
        raise ValueError("n must be >= 2")
    if isinstance(state, GaussianState):
        # Gaussian branch is vectorized (same kernel as wigner_plane); it must
        # stay single-mode to match the scalar wigner_gaussian contract.
        if state.nmode != 1:
            raise ValueError("wigner_grid: single-mode only")
        return _wigner_grid_gaussian(state.V, state.rbar, lim, n)
    xs = np.linspace(-lim, lim, n)
    ps = np.linspace(-lim, lim, n)
    X, P = np.meshgrid(xs, ps, indexing="xy")
    if isinstance(state, BosonicState):

        def fn(x: float, p: float) -> float:
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
