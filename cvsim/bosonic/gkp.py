"""Truncated |0⟩/|1⟩_GKP as Bosonic components (teaching).

1D (X basis): Dirac comb on x, spacing √(2π); V=½ diag(ε,1/ε).
2D (Z basis): single-mode square lattice — position comb x=kΔ, p=0, V=½ diag(ε,1/ε);
   |1⟩_2d = alternating-phase comb (peaks at the SAME x=kΔ as |0⟩, coefficient (−1)^k), the
   complementary logical basis to the 1d X basis (momentum comb emerges via Fourier).

|0⟩ 1d/2d: x=kΔ.  |1⟩ 1d: x=(k+½)Δ (X basis, half-period shift only).
   |1⟩ 2d: x=kΔ, coefficient (−1)^k (Z basis; peak does NOT move, only the phase alternates).

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

    B7 convention fix: the cross-term Wigner phase gradient is fixed by
    symplectic structure (``J·Δr``, V-independent); the component form
    ``exp(i δᵀ V⁻¹ s)`` matches at ``s = V·J·Δr`` (full difference). The old
    ``s = J·d`` (with ``d = Δr/2``) is only exact for isotropic V (cat
    V = I/2, where ``V·J·Δr = J·d``); for anisotropic V (GKP, squeezed
    components) it produced non-pure cross states (Wigner-integral probe:
    ``Tr(ρ²) = 0.226`` instead of 1).
    """
    r0 = np.asarray(r0, dtype=float).real
    r1 = np.asarray(r1, dtype=float).real
    m = 0.5 * (r0 + r1)
    # xxpp symplectic: maps x-difference into p-imag
    J = np.array([[0.0, 1.0], [-1.0, 0.0]], dtype=float)
    # B7: V-aware direction. Isotropic V=cI gives V@J@dr = 2c·J·d, which
    # reduces to the legacy J@d only for V=I/2 (cat); anisotropic V (GKP)
    # needs the full V@J@dr to be a pure cross state.
    s = V @ J @ (r0 - r1)
    # B7 convention: S_ij = ⟨g0|g1⟩ is folded into the cross weight
    # (w_c = c0·c1·S_ij / Z) so that weight_sum = Σw = 1 (public semantics)
    # and the Wigner kernel uses the bare no-S form.
    S_ij = _gauss_overlap(V, r0, r1)
    w_c = float(c0 * c1 * S_ij)
    for sign in (1.0, -1.0):
        rbar = m.astype(complex) + 1j * sign * s
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
    # Normalize by the actual component sum (Σw = 1 for every cross mode):
    # for full/nn, raw_w already includes the c_i·c_j·S_ij cross weights
    # (S folded into w, B7), so sum(raw_w) IS the Gram Z = c†Sc; for
    # none, raw_w is the diagonal sum only (mixed-by-design, no cross
    # components), which is the correct renormalization there too.
    for comp, w in zip(comps, raw_w, strict=False):
        comp.w = complex(w / s)
    return BosonicState(components=comps)


def _gkp_comb_peaks_and_coeffs(
    epsilon: float,
    grid_size: int,
    *,
    x_of_k: Callable[[int, float], float],
    alternate_phase: bool = False,
) -> tuple[list[np.ndarray], np.ndarray, list[float], list[int]]:
    """Shared comb geometry for both lattices (single source, no duplication).

    Returns ``(peaks, V, c, ks)``: single-mode position comb along x (p=0),
    V = ½diag(ε,1/ε) (squeezed vacuum, pure), envelope c_k ∝ exp(−½πεk²)
    times (−1)^k when ``alternate_phase`` (Z basis).
    """
    N = int(grid_size)
    delta = np.sqrt(2.0 * np.pi)
    V = 0.5 * np.diag([epsilon, 1.0 / epsilon])
    ks = list(range(-N, N + 1))
    peaks = [np.array([float(x_of_k(k, delta)), 0.0], dtype=float) for k in ks]
    # envelope a_k ∝ exp(−π ε k² / 2); Z basis (gkp1, 2d) multiplies by (−1)^k
    c = [
        float(np.exp(-0.5 * np.pi * epsilon * k * k) * ((-1.0) ** k if alternate_phase else 1.0))
        for k in ks
    ]
    return peaks, V, c, ks

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

    peaks, V, c, ks = _gkp_comb_peaks_and_coeffs(epsilon, grid_size, x_of_k=x_of_k)
    nn_pairs: list[tuple[int, int]] | None = None
    if cross == "nn" and int(grid_size) >= 1:
        # consecutive indices in ks
        nn_pairs = [(i, i + 1) for i in range(len(ks) - 1)]
    return _build_gram_state(peaks, V, c, cross=cross, nn_pairs=nn_pairs)

def _gkp_z_comb(
    epsilon: float,
    grid_size: int,
    *,
    cross: CrossMode,
    x_of_k: Callable[[int, float], float],
    alternate_phase: bool = False,
) -> BosonicState:
    """Single-mode square-lattice GKP (Z basis); cross none or full (nn not supported).

    Peaks are a single-mode position comb along x (p=0); the momentum comb and
    the logical-Z structure emerge via the width V=½diag(ε,1/ε) and (for
    ``alternate_phase``) the coefficient (−1)^k. This is the complementary
    (Z) logical basis to the 1d ``_gkp_x_comb`` (X basis, half-period shift).
    """
    if epsilon <= 0:
        raise ValueError(f"epsilon must be > 0, got {epsilon}")
    if grid_size < 0:
        raise ValueError(f"grid_size must be >= 0, got {grid_size}")
    if cross == "nn":
        raise ValueError("lattice='2d' does not support cross='nn' (use none or full)")
    if cross not in ("none", "full"):
        raise ValueError(f"cross must be 'none' or 'full' for 2d, got {cross!r}")

    peaks, V, c, _ = _gkp_comb_peaks_and_coeffs(
        epsilon, grid_size, x_of_k=x_of_k, alternate_phase=alternate_phase
    )
    return _build_gram_state(peaks, V, c, cross=cross)

def _dispatch(
    epsilon: float,
    grid_size: int,
    *,
    cross: CrossMode,
    lattice: LatticeMode,
    x_of_k: Callable[[int, float], float],
    alternate_phase: bool = False,
) -> BosonicState:
    if lattice not in ("1d", "2d"):
        raise ValueError(f"lattice must be '1d' or '2d', got {lattice!r}")
    if lattice == "1d":
        return _gkp_x_comb(epsilon, grid_size, cross=cross, x_of_k=x_of_k)
    return _gkp_z_comb(
        epsilon, grid_size, cross=cross, x_of_k=x_of_k, alternate_phase=alternate_phase
    )


def gkp0(
    epsilon: float = 0.1,
    grid_size: int = 3,
    *,
    cross: CrossMode = "none",
    lattice: LatticeMode = "1d",
) -> BosonicState:
    """Approximate |0⟩_GKP (shared by both logical bases).

    lattice="1d"/"2d": single-mode position comb peaks x=kΔ, V=½diag(ε,1/ε);
       cross none|nn(full for 1d; 2d supports none|full, not nn).
    Weights Gram-normalized Z=c†Sc. Not Clifford.
    """
    return _dispatch(
        epsilon,
        grid_size,
        cross=cross,
        lattice=lattice,
        x_of_k=lambda k, d: k * d,
        alternate_phase=False,
    )


def gkp1(
    epsilon: float = 0.1,
    grid_size: int = 3,
    *,
    cross: CrossMode = "none",
    lattice: LatticeMode = "1d",
) -> BosonicState:
    """Approximate |1⟩_GKP, basis depends on ``lattice``.

    lattice="1d" (X basis): half-period shift in x only vs gkp0 (peaks (k+½)Δ).
    lattice="2d" (Z basis): peaks at the SAME (kΔ,0) as gkp0, but coefficient
       (−1)^k (alternating phase) — the complementary logical basis. This means
       2d |1⟩ is NOT a peak shift; it differs only in the cross-component sign.
    Same K / cross rules as gkp0. Teaching Gram pure-state; not Clifford.
    """
    # per-basis map: (x_of_k, alternate_phase) — no if-cascade
    basis: dict[str, tuple[Callable[[int, float], float], bool]] = {
        "1d": (lambda k, d: (k + 0.5) * d, False),
        "2d": (lambda k, d: k * d, True),
    }
    if lattice not in basis:
        raise ValueError(f"lattice must be '1d' or '2d', got {lattice!r}")
    x_of_k, alternate_phase = basis[lattice]
    return _dispatch(
        epsilon,
        grid_size,
        cross=cross,
        lattice=lattice,
        x_of_k=x_of_k,
        alternate_phase=alternate_phase,
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

        .. note::
            Only valid for the 1d **X basis** (|1⟩ = half-period peak shift). For the
            2d **Z basis** (``lattice="2d"``) the |0⟩/|1⟩ difference is the alternating
            ``(−1)^k`` phase, which lives in the cross-component sign — this diagonal
            ``√w`` approximation drops it and would report ≈1 overlap. Use
            ``pure_fidelity`` there (it is the B7 complex-centre kernel).

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
