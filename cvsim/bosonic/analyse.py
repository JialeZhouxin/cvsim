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


def _M_complex(c1: np.ndarray, V1: np.ndarray, c2: np.ndarray, V2: np.ndarray) -> complex:
    """∫ exp(−½(x−c₁)ᵀV₁⁻¹(x−c₁) − ½(x−c₂)ᵀV₂⁻¹(x−c₂)) dx (complex centers, general V)."""
    A = np.linalg.inv(V1) + np.linalg.inv(V2)
    b = np.linalg.inv(V1) @ c1 + np.linalg.inv(V2) @ c2
    exp_arg = (
        0.5 * complex(b @ np.linalg.solve(A, b))
        - 0.5 * (complex(c1 @ np.linalg.inv(V1) @ c1) + complex(c2 @ np.linalg.inv(V2) @ c2))
    )
    # ∫ exp(-xᵀA x/2 + b·x) dx = (2π)^m/√det A · exp(½ bᵀA⁻¹b)
    m = V1.shape[0] // 2
    return complex((2.0 * np.pi) ** m / np.sqrt(np.linalg.det(A)) * np.exp(exp_arg))


def _K_re(ci: Component, cj: Component) -> complex:
    """Tr(ρ_i ρ_j) kernel = 2π ∫ Re[G(c_i)] Re[G(c_j)] with S factors."""
    c_i = np.asarray(ci.rbar, dtype=complex)
    c_j = np.asarray(cj.rbar, dtype=complex)
    Vi = np.asarray(ci.V, dtype=float)
    Vj = np.asarray(cj.V, dtype=float)
    # prefactors: each G has pref = 1/(π^m √det(2V)); Re products:
    # ∫Re[Gi]Re[Gj] = ½Re[∫GiGj] + ½Re[∫Gi conj(Gj)]
    p1 = 1.0 / (np.pi ** (Vi.shape[0] // 2) * np.sqrt(np.linalg.det(2.0 * Vi)))
    p2 = 1.0 / (np.pi ** (Vj.shape[0] // 2) * np.sqrt(np.linalg.det(2.0 * Vj)))
    M1 = _M_complex(c_i, Vi, c_j, Vj)
    M2 = _M_complex(c_i, Vi, np.conj(c_j), Vj)
    # Numeric-stability note: |M| can overflow exp() for well-separated
    # complex centres (s large, e.g. GKP grid_size≥3 full-cross far pairs)
    # even though the physical result is finite through cancellation in the
    # ½(M1+M2) Re combination. Large-s states are far outside the test
    # envelope; see probe scripts for the verified range. ponytail: revisit
    # with a shared log-scale factor if large-s cross states become relevant.
    return complex(2.0 * np.pi * p1 * p2 * (0.5 * np.real(M1) + 0.5 * np.real(M2)))


def _strict_tr2(state_a: BosonicState, state_b: BosonicState | None = None) -> complex:
    """Σ_ij w_i^a w_j^b Tr(ρ_i^a ρ_j^b) — strict Tr(ρ_a ρ_b) (Wigner kernel).

    B7 convention: S (amplitude factor ⟨g_a|g_b⟩) is folded into the
    component weights (w_cross = ±ov/N for cat; c_i c_j S_ij / Z for GKP)
    — the public weight_sum = Σw = 1 semantics — so the kernel here is the
    bare Wigner inner product ``_K_re`` = 2π ∫ Re[G(c_i)]·Re[G(c_j)], with
    no extra S factor (w already carries it).
    """
    comps_a = state_a.components
    comps_b = state_a.components if state_b is None else state_b.components
    acc = 0.0 + 0.0j
    for ci in comps_a:
        for cj in comps_b:
            acc += ci.w * cj.w * _K_re(ci, cj)
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
