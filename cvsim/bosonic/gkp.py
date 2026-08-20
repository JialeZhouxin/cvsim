"""Truncated |0⟩/|1⟩_GKP as Bosonic components (teaching).

1D: Dirac comb on x, spacing √(2π); V=½ diag(ε,1/ε).
2D: square lattice peaks on (x,p); V=(ε/2)I (isotropic).

|0⟩ 1d: x=kΔ;  |1⟩ 1d: x=(k+½)Δ;  k=-N…N.
|0⟩ 2d: (kΔ,lΔ); |1⟩ 2d: ((k+½)Δ, lΔ).

cross: none | nn (1d only) | full (1d & 2d).
Weights: pure-state Gram Z=c†Sc (same pattern as cat).
Not Clifford / not dual-basis / not stabilizer decode.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import numpy as np

from cvsim.bosonic.state import BosonicState, Component

CrossMode = Literal["none", "nn", "full"]
LatticeMode = Literal["1d", "2d"]


def _gauss_overlap_two_V(Va: np.ndarray, Vb: np.ndarray, r_i: np.ndarray, r_j: np.ndarray) -> float:
    """⟨g_a|g_b⟩ between equal-... general two-V pure Gaussians (B6).

    S = 2^m · (detVa·detVb)^{1/4} / √det(Va+Vb)
        · exp(−¼ Δrᵀ (Va+Vb)⁻¹ Δr),   Δr = r_i − r_j,  m = nmode.

    Real means (ħ=1); complex centers deferred to B7 bridges. At equal V
    this reduces exactly to ``_gauss_overlap``: det(2V)=2^{2m}detV ⇒ factor
    2^m·√detV/2^m·√detV = 1, leaving exp(−⅛ dr V⁻¹ dr).
    """
    Va = np.asarray(Va, dtype=float)
    Vb = np.asarray(Vb, dtype=float)
    ri = np.asarray(r_i, dtype=float).real
    rj = np.asarray(r_j, dtype=float).real
    m = Va.shape[0] // 2
    Sum = Va + Vb
    dr = ri - rj
    q = float(dr @ np.linalg.solve(Sum, dr))
    _, logdet_sum = np.linalg.slogdet(Sum)
    _, logdet_a = np.linalg.slogdet(Va)
    _, logdet_b = np.linalg.slogdet(Vb)
    factor = (2.0**m) * np.exp(0.25 * (logdet_a + logdet_b) - 0.5 * logdet_sum)
    return float(factor * np.exp(-0.25 * q))


def _gauss_overlap(V: np.ndarray, r_i: np.ndarray, r_j: np.ndarray) -> float:
    """⟨g_i|g_j⟩ for equal-V pure Gaussians, real means (ħ=1 teaching).

    S = exp(−⅛ Δrᵀ V⁻¹ Δr). Matches 1d: exp(−δx²/(4ε)); 2d: exp(−|Δr|²/(4ε)).
    Convenience wrapper over ``_gauss_overlap_two_V(V, V, r_i, r_j)``.
    """
    return _gauss_overlap_two_V(V, V, r_i, r_j)


def _append_cross_pair_vec(
    comps: list[Component],
    raw_w: list[float],
    V: np.ndarray,
    r0: np.ndarray,
    r1: np.ndarray,
    c0: float,
    c1: float,
) -> None:
    """Two complex-mean components for |g0⟩⟨g1| + h.c. (Gram pure-state).

    Real midpoint m; imag via symplectic J so 1d x-pair recovers r=(m, ±i d_x).
    J = [[0,1],[-1,0]]: J(d_x,0)=(0,-d_x); both ± signs cover ±i d_x on p.
    """
    r0 = np.asarray(r0, dtype=float).real
    r1 = np.asarray(r1, dtype=float).real
    ov = _gauss_overlap(V, r0, r1)
    m = 0.5 * (r0 + r1)
    d = 0.5 * (r0 - r1)
    # xxpp symplectic: maps x-difference into p-imag (legacy 1d GKP/cat)
    J = np.array([[0.0, 1.0], [-1.0, 0.0]], dtype=float)
    jd = J @ d
    w_c = float(c0 * c1 * ov)
    for sign in (1.0, -1.0):
        rbar = m.astype(complex) + 1j * sign * jd
        comps.append(Component(V=V.copy(), rbar=rbar, w=0.0 + 0.0j))
        raw_w.append(w_c)


def _build_gram_state(
    peaks: list[np.ndarray],
    V: np.ndarray,
    c: list[float],
    *,
    cross: CrossMode,
    nn_pairs: list[tuple[int, int]] | None = None,
) -> BosonicState:
    """Build BosonicState from peak means + Gram pure-state weights.

    diag: w_i ∝ c_i²; full pairs: w_ij± ∝ c_i c_j S_ij; Z = c† S c after renorm.
    """
    M = len(peaks)
    if M == 0:
        raise ValueError("empty peaks")
    if len(c) != M:
        raise ValueError("c length must match peaks")
    V = np.asarray(V, dtype=float)
    comps: list[Component] = []
    raw_w: list[float] = []

    for i in range(M):
        rbar = np.asarray(peaks[i], dtype=complex)
        comps.append(Component(V=V.copy(), rbar=rbar, w=0.0 + 0.0j))
        raw_w.append(float(c[i] * c[i]))

    if cross == "full":
        for i in range(M):
            for j in range(i + 1, M):
                _append_cross_pair_vec(comps, raw_w, V, peaks[i], peaks[j], c[i], c[j])
    elif cross == "nn":
        if not nn_pairs:
            pass
        else:
            for i, j in nn_pairs:
                _append_cross_pair_vec(comps, raw_w, V, peaks[i], peaks[j], c[i], c[j])

    s = sum(raw_w)
    if s <= 0:
        raise ValueError("weight sum non-positive")
    for comp, w in zip(comps, raw_w):
        comp.w = complex(w / s)
    return BosonicState(components=comps)


def _gkp_x_comb(
    epsilon: float,
    grid_size: int,
    *,
    cross: CrossMode,
    x_of_k: Callable[[int, float], float],
) -> BosonicState:
    if epsilon <= 0:
        raise ValueError(f"epsilon must be > 0, got {epsilon}")
    if grid_size < 0:
        raise ValueError(f"grid_size must be >= 0, got {grid_size}")
    if cross not in ("none", "nn", "full"):
        raise ValueError(f"cross must be 'none', 'nn', or 'full', got {cross!r}")

    N = int(grid_size)
    delta = np.sqrt(2.0 * np.pi)
    V = 0.5 * np.diag([epsilon, 1.0 / epsilon])
    ks = list(range(-N, N + 1))
    peaks = [np.array([float(x_of_k(k, delta)), 0.0], dtype=float) for k in ks]
    # envelope a_k ∝ exp(−π ε k² / 2)
    c = [float(np.exp(-0.5 * np.pi * epsilon * k * k)) for k in ks]
    nn_pairs: list[tuple[int, int]] | None = None
    if cross == "nn" and N >= 1:
        # consecutive indices in ks
        nn_pairs = [(i, i + 1) for i in range(len(ks) - 1)]
    return _build_gram_state(peaks, V, c, cross=cross, nn_pairs=nn_pairs)


def _gkp_xp_grid(
    epsilon: float,
    grid_size: int,
    *,
    cross: CrossMode,
    x_of_k: Callable[[int, float], float],
) -> BosonicState:
    """2D lattice peaks; cross none or full (nn not supported)."""
    if epsilon <= 0:
        raise ValueError(f"epsilon must be > 0, got {epsilon}")
    if grid_size < 0:
        raise ValueError(f"grid_size must be >= 0, got {grid_size}")
    if cross == "nn":
        raise ValueError("lattice='2d' does not support cross='nn' (use none or full)")
    if cross not in ("none", "full"):
        raise ValueError(f"cross must be 'none' or 'full' for 2d, got {cross!r}")

    N = int(grid_size)
    delta = np.sqrt(2.0 * np.pi)
    V = 0.5 * epsilon * np.eye(2, dtype=float)
    idxs = list(range(-N, N + 1))
    peaks: list[np.ndarray] = []
    c: list[float] = []
    for k in idxs:
        x = float(x_of_k(k, delta))
        for ell in idxs:
            p = float(ell * delta)
            peaks.append(np.array([x, p], dtype=float))
            c.append(float(np.exp(-0.5 * np.pi * epsilon * (k * k + ell * ell))))
    return _build_gram_state(peaks, V, c, cross=cross)


def _dispatch(
    epsilon: float,
    grid_size: int,
    *,
    cross: CrossMode,
    lattice: LatticeMode,
    x_of_k: Callable[[int, float], float],
) -> BosonicState:
    if lattice not in ("1d", "2d"):
        raise ValueError(f"lattice must be '1d' or '2d', got {lattice!r}")
    if lattice == "1d":
        return _gkp_x_comb(epsilon, grid_size, cross=cross, x_of_k=x_of_k)
    return _gkp_xp_grid(epsilon, grid_size, cross=cross, x_of_k=x_of_k)


def gkp0(
    epsilon: float = 0.1,
    grid_size: int = 3,
    *,
    cross: CrossMode = "none",
    lattice: LatticeMode = "1d",
) -> BosonicState:
    """Approximate |0⟩_GKP.

    lattice="1d": x-teeth; V=½diag(ε,1/ε); cross none|nn|full.
    lattice="2d": square grid; V=(ε/2)I; cross none|full (not nn).
    Weights Gram-normalized Z=c†Sc. Not Clifford.
    """
    return _dispatch(
        epsilon, grid_size, cross=cross, lattice=lattice, x_of_k=lambda k, d: k * d
    )


def gkp1(
    epsilon: float = 0.1,
    grid_size: int = 3,
    *,
    cross: CrossMode = "none",
    lattice: LatticeMode = "1d",
) -> BosonicState:
    """Approximate |1⟩_GKP: half-period shift in x only vs gkp0.

    Same K / cross / lattice rules as gkp0. Teaching Gram pure-state; not Clifford.
    """
    return _dispatch(
        epsilon,
        grid_size,
        cross=cross,
        lattice=lattice,
        x_of_k=lambda k, d: (k + 0.5) * d,
    )


def _diag_peaks(state: BosonicState) -> tuple[list[np.ndarray], list[float], np.ndarray]:
    """Real-mean components as peaks + sqrt(w) coeffs + shared V (teaching)."""
    peaks: list[np.ndarray] = []
    c: list[float] = []
    V = None
    for comp in state.components:
        r = np.asarray(comp.rbar, dtype=complex)
        if np.max(np.abs(r.imag)) > 1e-12:
            continue  # skip complex cross centres
        peaks.append(r.real.astype(float))
        w = float(np.real(comp.w))
        c.append(float(np.sqrt(max(w, 0.0))))
        if V is None:
            V = np.asarray(comp.V, dtype=float)
    if not peaks or V is None:
        raise ValueError("no real diagonal peaks in state")
    return peaks, c, V


def gkp_logical_overlap(state_a: BosonicState, state_b: BosonicState) -> complex:
    """Teaching logical-ish overlap via diagonal-peak Gram.

    .. deprecated::
        B1 (architecture A12): retained for teaching, but **deprecated** —
        it is a diagonal-peak approximation (real-mean components only) and
        is not the frozen core surface. Use the future closed-form
        ``pure_fidelity`` (B2/B4, Gaussian overlap kernel) for GKP logical
        fidelity. Behavior unchanged; do not build new code on it.

    Uses only real-mean components: c_i=√w_i, T_ij=⟨g_i^a|g_j^b⟩,
    ov = Σ_ij c_i c_j T_ij (self-overlap ≈1 for full Gram states).

    Honesty: not stabilizer decode; not full dual basis; ignores complex
    components except through diag renorm weights.
    """
    pa, ca, Va = _diag_peaks(state_a)
    pb, cb, Vb = _diag_peaks(state_b)
    if Va.shape != Vb.shape or not np.allclose(Va, Vb, atol=1e-10):
        raise ValueError("gkp_logical_overlap requires matching V on diag peaks")
    acc = 0.0 + 0.0j
    for i, ri in enumerate(pa):
        for j, rj in enumerate(pb):
            # use Va (equal)
            ov = _gauss_overlap(Va, ri, rj)
            acc += ca[i] * cb[j] * ov
    return complex(acc)
