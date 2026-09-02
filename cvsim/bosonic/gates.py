"""Bosonic gates: apply the same symplectic map to every component + kerr.

Gaussian gates (squeeze/displace/phase/...) map each component by a symplectic
S and keep weights fixed — the Gaussian manifold is closed. Kerr is a
NON-Gaussian gate: |n⟩ → e^{iχ n²} |n⟩, so a single Gaussian component is NOT
closed under it. We therefore EXPAND each input component into a sum of
complex Gaussian components (coherent-state superposition) that approximates
the Kerr evolution (see docs/phase0-kerr-component-expansion.md).
"""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.state import BosonicState, Component
from cvsim.symplectic import (
    S_CX,
    S_CZ,
    S_beamsplitter,
    S_from_unitary,
    S_mach_zehnder,
    S_phase,
    S_squeeze,
    S_two_mode_squeeze,
    d_displace,
)


# Minimal int cast for array indices (keeps mypy happy with np.arange).
def _as_int(v: float | np.integer) -> int:
    return int(v)


def _nmode(state: BosonicState) -> int:
    if not state.components:
        raise ValueError("empty BosonicState")
    return int(state.components[0].V.shape[0] // 2)


def apply_symplectic(
    state: BosonicState, S: np.ndarray, d: np.ndarray | None = None
) -> BosonicState:
    """V_k ← S V_k Sᵀ, r̄_k ← S r̄_k + d, w_k unchanged."""
    S = np.asarray(S, dtype=float)
    m2 = S.shape[0]
    d = np.zeros(m2, dtype=float) if d is None else np.asarray(d, dtype=float)
    out: list[Component] = []
    for c in state.components:
        V = S @ c.V @ S.T
        rbar = S @ c.rbar + d
        out.append(Component(V=V, rbar=rbar, w=c.w))
    return BosonicState(components=out)


def squeeze(state: BosonicState, r: float, mode: int = 0) -> BosonicState:
    m = _nmode(state)
    return apply_symplectic(state, S_squeeze(m, r, mode))


def displace(state: BosonicState, alpha: complex, mode: int = 0) -> BosonicState:
    m = _nmode(state)
    # D(α) is a pure phase-space translation in the Wigner representation
    # (Weyl shift): r̄ ← r̄ + d, V and w unchanged. The relative phase of
    # cross components is carried by Re[G(c)] itself (cos(δᵀV⁻¹s) term) —
    # adding a w phase here double-counts (displaced-cat fidelity 0.7696
    # instead of 0.79679).
    return apply_symplectic(state, np.eye(2 * m), d_displace(m, alpha, mode))


def phase(state: BosonicState, theta: float, mode: int = 0) -> BosonicState:
    m = _nmode(state)
    return apply_symplectic(state, S_phase(m, theta, mode))


def beamsplitter(
    state: BosonicState,
    mode1: int,
    mode2: int,
    theta: float,
    phi: float = 0.0,
) -> BosonicState:
    m = _nmode(state)
    return apply_symplectic(state, S_beamsplitter(m, mode1, mode2, theta, phi))


def two_mode_squeeze(state: BosonicState, r: float, mode1: int, mode2: int) -> BosonicState:
    m = _nmode(state)
    return apply_symplectic(state, S_two_mode_squeeze(m, r, mode1, mode2))


def fourier(state: BosonicState, mode: int = 0) -> BosonicState:
    """Fourier gate: phase rotation by π/2 on ``mode`` (â → iâ)."""
    return phase(state, 0.5 * np.pi, mode=mode)


def mach_zehnder(
    state: BosonicState,
    mode1: int,
    mode2: int,
    theta: float,
    phi: float = 0.0,
) -> BosonicState:
    """Mach–Zehnder: BS(θ) → phase(φ) on mode1 → BS(π/4)."""
    m = _nmode(state)
    return apply_symplectic(state, S_mach_zehnder(m, mode1, mode2, theta, phi))


def cz(state: BosonicState, weight: float, mode1: int, mode2: int) -> BosonicState:
    """Controlled-Z: CZ = exp(i·weight·x̂₁·x̂₂)."""
    m = _nmode(state)
    return apply_symplectic(state, S_CZ(m, weight, mode1, mode2))


def cx(state: BosonicState, weight: float, mode1: int, mode2: int) -> BosonicState:
    """Controlled-X: CX = exp(-i·weight·x̂₁·p̂₂)."""
    m = _nmode(state)
    return apply_symplectic(state, S_CX(m, weight, mode1, mode2))


def interferometer(state: BosonicState, U: np.ndarray, *, validate_u: bool = True) -> BosonicState:
    """Apply passive linear optics U (m×m unitary) to every component.

    ``validate_u=True`` (default) rejects non-unitary U. Setting
    ``validate_u=False`` is a **trusted escape hatch only**: a non-unitary U
    yields a non-symplectic S and can silently break physicality.
    """
    m = _nmode(state)
    U = np.asarray(U, dtype=complex)
    if U.shape != (m, m):
        raise ValueError(f"U shape {U.shape} incompatible with nmode={m}")
    S = S_from_unitary(U, validate=validate_u)
    return apply_symplectic(state, S)


# --- Kerr (non-Gaussian, component expansion) -----------------------------


def _fock_coherent_amp(alpha: complex, n: int) -> complex:
    """⟨n|α⟩ = e^{-|α|²/2} αⁿ / √(n!)."""
    import math

    return complex(np.exp(-0.5 * abs(alpha) ** 2) * alpha**n / float(math.factorial(n)) ** 0.5)


def _kerr_weights(alpha: complex, chi: float, q: int) -> tuple[list[complex], list[complex]]:
    """Heuristic Kerr expansion coefficients (pure-state amplitudes).

    Exact Kerr phase e^{iχn²} on a coherent state is approximated by q equal-
    angle coherent-state components α_k = α·e^{2πik/q} with amplitudes c_k
    solved by least squares against the truncated Fock target. These c_k are
    raw pure-state amplitudes; the density (Hermitian, Gram-normalised)
    decomposition is handled by ``_kerr_coherent_components``. Returns
      (alphas, amplitudes).
    """
    cutoff = max(3, int(abs(alpha) ** 2 * 2 + 10))
    n = np.arange(cutoff)
    target = np.array(
        [np.exp(1j * chi * kk * kk) * _fock_coherent_amp(alpha, _as_int(kk)) for kk in n],
        dtype=complex,
    )
    alphas = [alpha * np.exp(2j * np.pi * k / q) for k in range(q)]
    M = np.array(
        [[_fock_coherent_amp(ak, _as_int(kk)) for ak in alphas] for kk in n],
        dtype=complex,
    )
    # Complex least-squares via the normal equations (mypy-safe; np.linalg.lstsq
    # is typed for real inputs but supports complex numerically).
    Mh = M.conj().T
    gram = Mh @ M
    rhs = Mh @ target
    ck = np.linalg.solve(gram, rhs)
    return alphas, [complex(c) for c in np.asarray(ck, dtype=complex)]


def _kerr_coherent_components(
    comp: Component, chi: float, mode: int, q: int
) -> list[Component]:
    """Expand one Gaussian component under Kerr into components (diag + cross).

    Physics (docs/phase0-kerr-component-expansion.md): e^{iχ n²}|α⟩ splits into
    a superposition of coherent states |α_k⟩. For the pure state |ψ⟩=Σ_k c_k|α_k⟩
    its density ρ=|ψ⟩⟨ψ| decomposes exactly like ``_build_gram_state`` (gkp.py):
      diagonal (k,k):  real centre m_k, raw weight |c_k|²
      cross (k,l):     complex centre m ± i·V·J·Δr, raw weight c_k·conj(c_l)·S_kl
    Normalised by s = Σ raw_w (Gram Z = c†S c). Vacuum (|α|≈0) unchanged.
    """
    m2 = comp.V.shape[0]
    m = m2 // 2
    # Extract coherent mean α on `mode` (xxpp): x=√2 Re α, p=√2 Im α.
    x = float(np.real(comp.rbar[mode]))
    p = float(np.real(comp.rbar[m + mode]))
    alpha = (x / np.sqrt(2.0)) + 1j * (p / np.sqrt(2.0))

    # Vacuum: Kerr phase e^{iχ·0}=1 → leave the component unchanged.
    if abs(alpha) < 1e-12:
        return [comp]

    alphas, ck = _kerr_weights(alpha, chi, q)
    V = comp.V
    J = np.zeros((m2, m2), dtype=float)
    for mm in range(m):
        J[mm, m + mm] = 1.0
        J[m + mm, mm] = -1.0

    # Real position vectors m_k = √2 (Re α_k, Im α_k) in xxpp.
    mk = [np.zeros(m2, dtype=float) for _ in alphas]
    for k, ak in enumerate(alphas):
        mk[k][mode] = np.sqrt(2.0) * ak.real
        mk[k][m + mode] = np.sqrt(2.0) * ak.imag

    comps: list[Component] = []
    raw_w: list[complex] = []
    # Diagonal components (real centres).
    for k in range(q):
        comps.append(Component(V=V.copy(), rbar=mk[k].astype(complex), w=0.0 + 0.0j))
        raw_w.append(abs(ck[k]) ** 2)
    # Cross components: for each ordered pair (k,l), k≠l, emit the Hermitian
    # combination |g_k><g_l| + |g_l><g_k| as two complex-centre components.
    # Weight = Re[c_k conj(c_l) S_kl] (real) so the ± pair closes hermitian.
    for k in range(q):
        for j in range(q):
            if k == j:
                continue
            m_c = 0.5 * (mk[k] + mk[j])
            dr = mk[k] - mk[j]
            s_vec = V @ J @ dr
            diag = float(dr @ np.linalg.solve(V, dr))
            S_kl = float(np.exp(-0.25 * diag)) if abs(dr).sum() > 1e-15 else 1.0
            w_cross = complex(ck[k] * np.conj(ck[j]) * S_kl)
            # |g_k><g_l| + |g_l><g_k| is Hermitian; its two ± centres carry weight
            # Re(w_cross). The imaginary part lives in the Wigner cos(δᵀV⁻¹s)
            # kernel, not the weight (B7 convention), so take the real part.
            weight = complex(w_cross.real)
            for sign in (1.0, -1.0):
                rbar = m_c.astype(complex) + 1j * sign * s_vec
                comps.append(Component(V=V.copy(), rbar=rbar, w=0.0 + 0.0j))
                raw_w.append(weight)

    s = sum(raw_w)
    # Gram Z = c†S c is real for any pure state; take .real for a real normaliser.
    s = complex(s.real)
    if abs(s) <= 1e-15:
        raise ValueError("kerr: Gram normalization sum non-positive / zero")
    for comp_out, w in zip(comps, raw_w, strict=False):
        comp_out.w = comp.w * complex(w / s)
    return comps


def kerr(state: BosonicState, chi: float, mode: int = 0, q: int | None = None) -> BosonicState:
    """Kerr gate: |n⟩ → e^{iχ n²} |n⟩, non-Gaussian (component expansion).

    Each input Gaussian component is expanded into components (diagonal real-
    centre + cross complex-centre) approximating the Kerr phase action. ``q``
    defaults to an auto-chosen value ``max(2, round(2π/χ))`` matching the Kerr
    phase closed-loop (χ=π→2, χ=π/2→4, χ=2π/3→3 or 6, ...) which is exact for
    those symmetric χ and numerically stable; a large ``q`` on a non-matching
    χ can make the least-squares fit ill-conditioned. Vacuum is left unchanged
    (e^{iχ·0}=1). Does NOT preserve the Gaussian manifold (K=1 grows).
    """
    m = _nmode(state)
    if not 0 <= mode < m:
        raise IndexError(f"mode {mode} out of range for nmode={m}")
    if q is None:
        qi = int(round(2.0 * np.pi / chi)) if chi > 0 else 2
        q = max(2, min(16, qi))
    out: list[Component] = []
    for c in state.components:
        out.extend(_kerr_coherent_components(c, chi, mode, q))
    return BosonicState(components=out)
