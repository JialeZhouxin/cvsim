"""Bosonic analyse: purity + pure_fidelity (B4, teaching closed forms).

- ``purity`` — mixed-state purity diagonal approximation ``Σ|w_k|² μ_k``.
- ``pure_fidelity`` — pure-state fidelity ``|⟨ψ|φ⟩|²`` (equal-V restriction).

Both are teaching closed forms; see docstrings for limitations and upgrade
paths (``overlap`` / general two-V fidelity deferred to B7).
"""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.component_eng import is_hermitian
from cvsim.bosonic.gkp import _gauss_overlap
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
            raise ValueError(
                f"purity: det(V_k) ≤ 0 (slogdet sign={sign}): non-physical/singular"
            )
        mu_k = float(np.exp(-0.5 * logdet) / (2**m))
        acc += abs(c.w) ** 2 * mu_k
    return float(acc)


def pure_fidelity(state_a: BosonicState, state_b: BosonicState) -> float:
    """Pure-state fidelity ``|⟨ψ|φ⟩|²`` (equal-V restriction).

    ``|ψ⟩ = Σ_i c_i |g_i⟩``, ``|φ⟩ = Σ_j d_j |g_j'⟩`` with **equal V** across
    all components of both states. Gram matrix
    ``T[i,j] = _gauss_overlap(V, r_i^a, r_j^b)``, inner product
    ``⟨ψ|φ⟩ = c_aᴴ · T · c_b`` (c = √w, complex roots preserve phase).

    **Limitation**: requires all component covariances of both states to be
    equal (same V). General two-V Gaussian overlap (Braunstein formula) is
    deferred to B7 bridges.

    Raises
    ------
    ValueError
        If component V matrices differ across the two states.
    """
    comps_a = state_a.components
    comps_b = state_b.components
    V_ref = comps_a[0].V
    for c in comps_a:
        if not np.allclose(c.V, V_ref, atol=1e-10):
            raise ValueError("pure_fidelity: components of state_a have differing V")
    for c in comps_b:
        if not np.allclose(c.V, V_ref, atol=1e-10):
            raise ValueError("pure_fidelity: state_b V differs from state_a V (equal-V only)")
    # c vectors (complex sqrt of weights, phase preserved)
    c_a = np.array([np.sqrt(c.w) for c in comps_a], dtype=complex)
    c_b = np.array([np.sqrt(c.w) for c in comps_b], dtype=complex)
    # Gram matrix T[i,j] = ⟨g_i^a|g_j^b⟩ (real means; _gauss_overlap takes real)
    r_a = [c.rbar.real for c in comps_a]
    r_b = [c.rbar.real for c in comps_b]
    T = np.zeros((len(comps_a), len(comps_b)), dtype=float)
    for i, ri in enumerate(r_a):
        for j, rj in enumerate(r_b):
            T[i, j] = _gauss_overlap(V_ref, ri, rj)
    inner = c_a.conj() @ T @ c_b
    return float(abs(inner) ** 2)
