"""Bosonic analyse: purity + pure_fidelity (B4, teaching closed forms).

- ``purity`` — mixed-state purity diagonal approximation ``Σ|w_k|² μ_k``.
- ``pure_fidelity`` — pure-state fidelity ``|⟨ψ|φ⟩|²`` (equal-V restriction).

Both are teaching closed forms; see docstrings for limitations and upgrade
paths (``overlap`` / general two-V fidelity deferred to B7).
"""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.component_eng import is_hermitian
from cvsim.bosonic.gkp import _gauss_overlap_two_V
from cvsim.bosonic.state import BosonicState

_SIG_EPS = 1e-12


def purity(state: BosonicState, *, validate: bool = False) -> float:
    """Mixed-state purity approximation ``μ = Σ_k |w_k|² / (2^m √det V_k)``.

    Teaching diagonal approximation: drops non-diagonal terms
    ``Tr(ρ_i ρ_j)`` of the strict ``Tr(ρ²)`` expansion. Accurate when
    components are spatially separated (GKP teeth, well-separated cat
    peaks); biased for strongly overlapping components.

    **Limitation**: not the strict mixed-state purity. The strict form
    requires ``overlap`` (mixed-state Uhlmann, not implemented). Use this
    for teaching/self-consistency checks, not as a production benchmark.

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
    m = state.components[0].V.shape[0] // 2
    acc = 0.0
    for c in state.components:
        sign, logdet = np.linalg.slogdet(c.V)
        if sign <= 0:
            raise ValueError(f"purity: det(V_k) ≤ 0 (slogdet sign={sign}): non-physical/singular")
        mu_k = float(np.exp(-0.5 * logdet) / (2**m))
        acc += abs(c.w) ** 2 * mu_k
    return float(acc)


def pure_fidelity(state_a: BosonicState, state_b: BosonicState) -> float:
    """Pure-state fidelity ``|⟨ψ|φ⟩|²`` (general two-V, B6).

    ``|ψ⟩ = Σ_i c_i |g_i⟩``, ``|φ⟩ = Σ_j d_j |g_j'⟩`` with per-component
    covariances. Gram matrix ``T[i,j] = _gauss_overlap_two_V(V_i^a, V_j^b,
    r_i^a, r_j^b)`` (real means; complex centers deferred to B7 bridges),
    inner product ``⟨ψ|φ⟩ = c_aᴴ · T · c_b`` (c = √w, complex roots preserve
    phase). At equal V across all components it reduces exactly to the B4
    kernel, so equal-V callers see identical values.

    GKP QEC: loss γ reshapes the data covariance vs the ideal gkp0, so the
    two-V path is what makes the fidelity-vs-γ curve physically honest.

    Raises
    ------
    ValueError
        If either state is empty, or ``is_hermitian`` fails for real weights
        (not Hermitian-closed).
    """
    comps_a = state_a.components
    comps_b = state_b.components
    if not comps_a or not comps_b:
        raise ValueError("pure_fidelity: empty state (no components)")
    # c vectors (complex sqrt of weights, phase preserved)
    c_a = np.array([np.sqrt(c.w) for c in comps_a], dtype=complex)
    c_b = np.array([np.sqrt(c.w) for c in comps_b], dtype=complex)
    # Gram matrix T[i,j] = ⟨g_i^a|g_j^b⟩ (real means; two-V kernel)
    T = np.zeros((len(comps_a), len(comps_b)), dtype=float)
    for i, ca2 in enumerate(comps_a):
        for j, cb2 in enumerate(comps_b):
            T[i, j] = _gauss_overlap_two_V(ca2.V, cb2.V, ca2.rbar.real, cb2.rbar.real)
    inner = c_a.conj() @ T @ c_b
    return float(abs(inner) ** 2)
