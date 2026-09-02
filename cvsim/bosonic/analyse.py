"""Bosonic analyse: purity + pure_fidelity (B7, complex-centre exact kernel).

Physical model: a state's Wigner function is the real sum over components
``W_phys = Σ_k w_k · S_k · Re[G(c_k)]`` where ``G(c) = pref·exp(−½(x−c)ᵀV⁻¹(x−c))``
is the complex-center (analytic-continuation) Wigner, ``c_k = μ_k + i s_k``
(``s_k`` from Wigner's symplectic gradient) and ``S_k = ⟨g_a|g_b|⟩`` is the
component's amplitude factor (pure-Gaussian overlap of its centre pair;
1 for diagonal components). ``wigner_point_gaussian`` implements ``Re[G]``
(incl. the ``exp(+½sᵀV⁻¹s)`` boost, which is what makes ``e^{½sV⁻¹s} = 1/S``
for V = I/2 cross terms).

The exact matrix element (overlap of two components) is the Wigner-function
inner product
    ``Tr(ρ_i ρ_j) = 2π ∫ Re[G(c_i)]·Re[G(c_j)] dx  (= S_i S_j · K_Re)``
with the closed form (probe-verified to 1e-14)
    ``K_Re = ½Re[M(c_i, c_j)] + ½Re[M(c_i, conj(c_j))]``,
    ``M(c1,c2) = (2π)^m/√det(A)·…`` Gaussian integral of the two complex
    gaussians (identical V only needs the "same-V" branch).

This is the *bilinear* continuation: exact for interference components
(cat, GKP cross, conditioned states) at any V (pure or thermal — loss /
amplifier heat the per-component covariance and the kernel stays exact).
The old ``|⟨g_i|g_j⟩|²`` form is a quadrilinear contraction that is only
reliable for real centres (the silent-complex-centre bug).

Component→pair mapping: ``m = ½(r_i+r_j)``, ``s = V·J·(r_j−r_i)`` (B7), so
``r_j − r_i = −J·V⁻¹·s``; diagonal components (s=0) are ``(r, r)``.

Note (B7): the identity ``Tr(|g_i⟩⟨g_j|·|g_c⟩⟨g_d|) = ⟨g_j|g_c⟩⟨g_d|g_i⟩``
holds only for *pure* (rank-1) components; once a channel thermalizes V the
Wigner-inner-product kernel above is the correct general form.
"""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.component_eng import is_hermitian
from cvsim.bosonic.state import BosonicState, Component

# Log-domain floor: float64 subnormal limit is ~4.9e-324 (ln ≈ −744.4).
# Any per-pair Tr(ρᵢρⱼ) contribution whose total log-scale falls below this
# is physically 0 (the weights/envelope have already underflowed); skipping
# the exp() avoids both 0·inf=nan and subnormal precision garbage.
_LOG_CUTOFF = -745.0


def _M_complex_log(
    c1: np.ndarray, V1: np.ndarray, c2: np.ndarray, V2: np.ndarray
) -> tuple[float, float]:
    """log|M| + arg of the complex-centre Gaussian integral M.

    Returns ``(log|M|, arg)`` so ``M = exp(log|M|)·exp(i·arg)``. Kept entirely
    in the log domain — ``log|M|`` may be hundreds in magnitude (e.g. GKP
    grid_size≥3 full-cross far pairs) but is a plain float, never ``exp``'d
    here, so no overflow.
    """
    A = np.linalg.inv(V1) + np.linalg.inv(V2)
    b = np.linalg.inv(V1) @ c1 + np.linalg.inv(V2) @ c2
    exp_arg = (
        0.5 * complex(b @ np.linalg.solve(A, b))
        - 0.5 * (complex(c1 @ np.linalg.inv(V1) @ c1) + complex(c2 @ np.linalg.inv(V2) @ c2))
    )
    # ∫ exp(-xᵀA x/2 + b·x) dx = (2π)^m/√det A · exp(½ bᵀA⁻¹b)
    m = V1.shape[0] // 2
    _, logdet_A = np.linalg.slogdet(A)
    log_abs = m * np.log(2.0 * np.pi) - 0.5 * logdet_A + exp_arg.real
    return log_abs, exp_arg.imag


def _K_pair(ci: Component, cj: Component) -> complex:
    """Per-pair ``w_i·w_j·Tr(ρ_i ρ_j)`` (B7 strict-kernel term), log-domain merged.

    ``Tr(ρ_i ρ_j) = 2π ∫ Re[G(c_i)]·Re[G(c_j)] = ½Re[M_i_j] + ½Re[M_i_j*]`` where
    ``M`` is the complex-centre Gaussian integral. The S (amplitude) factor is
    already folded into the component weights, so only the bare Wigner kernel
    is used. The w amplitude factor *cancels* the large ``exp(+½sᵀV⁻¹s)`` boost
    of far cross pairs (``JVJ=−¼V⁻¹`` identity) — analytically exact, but in
    float the boost ``exp(+754)`` and the weight ``exp(−823)`` each go out of
    range before meeting. This computes ``log|w_i| + log|w_j| + log|M_kernel|``
    in the log domain first, then only exponentiates a genuinely representable
    result (or yields 0 for subnormal-scale contributions).
    """
    c_i = np.asarray(ci.rbar, dtype=complex)
    c_j = np.asarray(cj.rbar, dtype=complex)
    Vi = np.asarray(ci.V, dtype=float)
    Vj = np.asarray(cj.V, dtype=float)
    m = Vi.shape[0] // 2
    # prefactors: each G has pref = 1/(π^m √det(2V)); combined with the
    # kernel 2π·½, log_lpre = log(2π) + log pᵢ + log pⱼ + log(½).
    _, logdet_2Vi = np.linalg.slogdet(2.0 * Vi)
    _, logdet_2Vj = np.linalg.slogdet(2.0 * Vj)
    log_lpre = np.log(2.0 * np.pi) - m * np.log(np.pi) - 0.5 * logdet_2Vi \
        - m * np.log(np.pi) - 0.5 * logdet_2Vj + np.log(0.5)
    # M1 = ∫ G_i G_j, M2 = ∫ G_i conj(G_j): log-domain values.
    log_a1, phase1 = _M_complex_log(c_i, Vi, c_j, Vj)
    log_a2, phase2 = _M_complex_log(c_i, Vi, np.conj(c_j), Vj)
    # Re[M] = exp(log_a)·cos(phase). Combine M1,M2 sharing a common scale
    # amax so the brackets exp(log_a − amax) ≤ 1 never overflow.
    amax = max(log_a1, log_a2)
    bracket = np.exp(log_a1 - amax) * np.cos(phase1) \
        + np.exp(log_a2 - amax) * np.cos(phase2)
    # Total log-scale: weights + kernel amplitude prefactor + shared boost.
    # w is complex (phase carries interference sign, e.g. (—1)^k for 2d Z;
    # cat cross weights can be ±i). Keep magnitude in log domain and carry
    # the phase separately so complex w isn't truncated.
    wi = complex(ci.w)
    wj = complex(cj.w)
    log_w_mag = np.log(abs(wi)) + np.log(abs(wj)) if wi and wj else -np.inf
    w_phase = np.angle(wi) + np.angle(wj)
    total_log = log_w_mag + log_lpre + amax
    if not np.isfinite(total_log) or total_log < _LOG_CUTOFF:
        return 0.0 + 0.0j
    real_amp = bracket * np.exp(total_log)
    return complex(real_amp * np.exp(1j * w_phase))


def _strict_tr2(state_a: BosonicState, state_b: BosonicState | None = None) -> complex:
    """Σ_ij w_i^a w_j^b Tr(ρ_i^a ρ_j^b) — strict Tr(ρ_a ρ_b) (Wigner kernel).

    B7 convention: S (amplitude factor ⟨g_a|g_b⟩) is folded into the
    component weights (w_cross = ±ov/N for cat; c_i c_j S_ij / Z for GKP)
    — the public weight_sum = Σw = 1 semantics — so the kernel here is the
    bare Wigner inner product, with no extra S factor (w already carries it).

    Per-pair terms go through ``_K_pair``, which absorbs ``w_i·w_j`` and
    merges everything in the log domain (``_LOG_CUTOFF``) so far-pair
    complex-centre exponentials never overflow (B7 numeric stability).
    """
    comps_a = state_a.components
    comps_b = state_a.components if state_b is None else state_b.components
    acc = 0.0 + 0.0j
    for ci in comps_a:
        for cj in comps_b:
            acc += _K_pair(ci, cj)
    return acc


def purity(state: BosonicState, *, validate: bool = False) -> float:
    """Mixed-state purity ``Tr(ρ²) = Σ_ij w_i w_j S_i S_j Tr(ρ_i ρ_j)`` (strict, B7).

    Wigner-inner-product kernel: exact for complex centres (cat/GKP cross,
    conditioned states) and for thermalized components (post-channel). The
    old diagonal / real-mean Gram undercounted interference.

    Parameters
    ----------
    validate :
        If True, raise ``ValueError`` when ``is_hermitian`` fails.

    Raises
    ------
    ValueError
        If ``det(V_k) ≤ 0`` (non-physical / singular) for any component,
        or if ``validate=True`` and the state is not Hermitian-closed.
    """
    if validate and not is_hermitian(state):
        raise ValueError("purity: state not Hermitian-closed (is_hermitian)")
    for c in state.components:
        sign, _ = np.linalg.slogdet(c.V)
        if sign <= 0:
            raise ValueError(
                f"purity: det(V_k) ≤ 0 (slogdet sign={sign}): singular/δ-projection — "
                f"Tr(ρ²) diverges for a delta Wigner, not a finite density matrix"
            )
    acc = _strict_tr2(state)
    if abs(acc.imag) > 1e-8:
        raise ValueError(f"purity: non-real Tr(ρ²) (imag={acc.imag:.3e}) — not Hermitian-closed")
    return float(acc.real)


def pure_fidelity(state_a: BosonicState, state_b: BosonicState) -> float:
    """State overlap ``Tr(ρ_a ρ_b)``; pure states → ``|⟨ψ|φ⟩|²`` (general V, B7).

    Raises
    ------
    ValueError
        If either state is empty.
    """
    comps_a = state_a.components
    comps_b = state_b.components
    if not comps_a or not comps_b:
        raise ValueError("pure_fidelity: empty state (no components)")
    for c in list(comps_a) + list(comps_b):
        sign, _ = np.linalg.slogdet(c.V)
        if sign <= 0:
            raise ValueError(
                f"pure_fidelity: det(V_k) ≤ 0 (slogdet sign={sign}): singular/δ-projection — "
                f"Tr(ρₐρ_b) diverges for a delta Wigner, not a finite density matrix"
            )
    acc = _strict_tr2(state_a, state_b)
    if abs(acc.imag) > 1e-8:
        raise ValueError(f"pure_fidelity: non-real Tr(ρ_a ρ_b) (imag={acc.imag:.3e})")
    return float(acc.real)
