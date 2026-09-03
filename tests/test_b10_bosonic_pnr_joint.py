"""B10 Bosonic joint multimode PNR probabilities and sampling (Phase 2a).

Anchors (PRD R7): TMSV (correlated block-diagonal V), cat⊗coherent
(product factorisation), cat⊗cat (complex-centre interference + entanglement).
GKP⊗GKP (cross) is a finite/non-negative/normalisation smoke only (no numeric
anchor, per ADR-0001 cross-rep discipline).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from cvsim.bosonic import (
    BosonicState,
    Component,
    coherent,
    pnr_probs,
    pnr_sample,
    two_mode_squeeze,
)
from cvsim.fock import FockState

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _cat_components(alpha: float) -> list[Component]:
    """Even cat |α⟩+|−α⟩ as 4 Gaussian components (xxpp, p-slot complex centres)."""
    ov = math.exp(-2.0 * alpha**2)
    norm = 2.0 * (1.0 + ov)
    V = 0.5 * np.eye(2)
    return [
        Component(V.copy(), np.array([np.sqrt(2.0) * alpha, 0.0]), 1.0 / norm),
        Component(V.copy(), np.array([-np.sqrt(2.0) * alpha, 0.0]), 1.0 / norm),
        Component(V.copy(), np.array([0.0, 1j * np.sqrt(2.0) * alpha]), ov / norm),
        Component(V.copy(), np.array([0.0, -1j * np.sqrt(2.0) * alpha]), ov / norm),
    ]

def _cat2_grouped_state(alpha: float) -> BosonicState:
    """cat⊗cat as a 2-mode BosonicState (grouped xxpp [x0,x1,p0,p1])."""
    V = 0.5 * np.eye(4)
    comps: list[Component] = []
    for r1, w1 in [(c.rbar, c.w) for c in _cat_components(alpha)]:
        for r2, w2 in [(c.rbar, c.w) for c in _cat_components(alpha)]:
            rb = np.zeros(4, dtype=complex)
            rb[0] = r1[0]   # x0
            rb[2] = r1[1]   # p0
            rb[1] = r2[0]   # x1
            rb[3] = r2[1]   # p1
            comps.append(Component(V.copy(), rb, complex(w1 * w2)))
    return BosonicState(comps)

# ---------------------------------------------------------------------------
# AC-1: TMSV joint diagonal + subset + single-mode equivalence
# ---------------------------------------------------------------------------

def test_b10_tmsv_joint_matches_analytic() -> None:
    r = 0.5
    cutoff = 10
    state = two_mode_squeeze(BosonicState.vacuum(2), r, 0, 1)
    p = pnr_probs(state, modes=None, cutoff=cutoff)
    assert p.shape == (cutoff, cutoff)
    assert p.dtype == np.float64
    lam = np.tanh(r)
    analytic = np.zeros((cutoff, cutoff))
    for n in range(cutoff):
        analytic[n, n] = lam ** (2 * n) / np.cosh(r) ** 2
    np.testing.assert_allclose(p, analytic, atol=1e-6)
    # diagonal order not mixed: n1 ≠ n2 must vanish (interference structure)
    np.testing.assert_allclose(p - np.diag(np.diag(p)), 0.0, atol=1e-9)

def test_b10_tmsv_subset_equals_full_marginal() -> None:
    r = 0.5
    cutoff = 10
    state = two_mode_squeeze(BosonicState.vacuum(2), r, 0, 1)
    joint = pnr_probs(state, modes=None, cutoff=cutoff)
    subset0 = pnr_probs(state, modes=(0,), cutoff=cutoff)
    marg0 = joint.sum(axis=1)
    np.testing.assert_allclose(subset0, marg0, atol=1e-6)

def test_b10_length1_tuple_equals_single_mode_path() -> None:
    state = two_mode_squeeze(BosonicState.vacuum(2), 0.5, 0, 1)
    tuple_path = pnr_probs(state, modes=(0,), cutoff=12)
    single_path = pnr_probs(state, mode=0, cutoff=12)
    assert tuple_path.shape == (12,)
    np.testing.assert_allclose(tuple_path, single_path, atol=1e-9)

# ---------------------------------------------------------------------------
# AC-2: cat⊗coherent product factorisation
# ---------------------------------------------------------------------------

def test_b10_cat_coherent_product_factorises() -> None:
    alpha, beta = 0.8, 0.6
    cutoff = 12
    p_cat = pnr_probs(BosonicState(_cat_components(alpha)), cutoff=cutoff)
    p_coh = pnr_probs(coherent(beta), cutoff=cutoff)
    # Build the 2-mode grouped product state (cat on mode 0, coherent on mode 1).
    V = 0.5 * np.eye(4)
    comps = []
    for c in _cat_components(alpha):
        rb = np.zeros(4, dtype=complex)
        rb[0] = c.rbar[0]
        rb[2] = c.rbar[1]
        rb[1] = np.sqrt(2.0) * beta
        comps.append(Component(V.copy(), rb, c.w))
    p_joint = pnr_probs(BosonicState(comps), modes=None, cutoff=cutoff)
    expected = np.outer(p_cat, p_coh)
    np.testing.assert_allclose(p_joint, expected, atol=1e-8)

# ---------------------------------------------------------------------------
# AC-3: cat⊗cat complex-centre interference vs fock gold
# ---------------------------------------------------------------------------

def test_b10_cat_cat_interference_matches_fock() -> None:
    alpha = 0.7
    cutoff = 10
    state = _cat2_grouped_state(alpha)
    p = pnr_probs(state, modes=None, cutoff=cutoff)
    # fock gold: cat ⊗ cat
    fc = FockState.coherent(70, alpha)
    minus = FockState.coherent(70, -alpha)
    amps = fc.amps + minus.amps
    amps /= np.linalg.norm(amps)
    gold = np.abs(np.kron(amps, amps).reshape(70, 70)[:cutoff, :cutoff]) ** 2
    np.testing.assert_allclose(p, gold, atol=1e-5)

def test_b10_entangled_state_joint_not_product() -> None:
    # A genuinely entangled (non-product) two-mode state: a 4-coherent
    # superposition with unequal weights → joint ≠ product of marginals.
    # |Ψ⟩ ∝ Σ c_{s1s2}|s1⟩|s2⟩, c asymmetric → entanglement.
    alpha = 0.7
    cutoff = 10
    weights = {(1, 1): 1.0, (1, -1): 0.6, (-1, 1): 0.4, (-1, -1): 0.3}
    V = 0.5 * np.eye(4)
    comps: list[Component] = []
    for (s1, s2), wgt in weights.items():
        rb = np.zeros(4, dtype=complex)
        rb[0] = np.sqrt(2.0) * s1 * alpha   # x0
        rb[1] = np.sqrt(2.0) * s2 * alpha   # x1
        comps.append(Component(V.copy(), rb, complex(wgt)))
    state = BosonicState(comps)
    p = pnr_probs(state, modes=None, cutoff=cutoff)
    m0 = p.sum(axis=1)
    m1 = p.sum(axis=0)
    naive = np.outer(m0, m1)
    # Entangled state → joint differs from the product of marginals.
    assert np.max(np.abs(p - naive)) > 1e-6

# ---------------------------------------------------------------------------
# AC-4: modes validation matrix
# ---------------------------------------------------------------------------

def test_b10_modes_validation() -> None:
    state = two_mode_squeeze(BosonicState.vacuum(2), 0.5, 0, 1)
    # TypeError: bare int / bool passed as modes
    for bad in (0, True, 1.5):
        with pytest.raises(TypeError):
            pnr_probs(state, modes=bad)  # type: ignore[arg-type]
    # ValueError: duplicate indices / empty tuple
    with pytest.raises(ValueError):
        pnr_probs(state, modes=(0, 0), cutoff=5)
    with pytest.raises(ValueError):
        pnr_probs(state, modes=(), cutoff=5)
    # IndexError: out of range
    with pytest.raises(IndexError):
        pnr_probs(state, modes=(5,), cutoff=5)
    # TypeError: mode + modes mutually exclusive
    with pytest.raises(TypeError):
        pnr_probs(state, 0, modes=(1,), cutoff=5)
    with pytest.raises(TypeError):
        pnr_sample(state, 1, modes=(0,), cutoff=5)
    # length-1 tuple allowed (tensor path)
    p = pnr_probs(state, modes=(0,), cutoff=5)
    assert p.shape == (5,)

# ---------------------------------------------------------------------------
# AC-5: pnr_sample joint tuple + seed reproducibility + edge consistency
# ---------------------------------------------------------------------------

def test_b10_pnr_sample_joint_tuple_and_seed() -> None:
    state = two_mode_squeeze(BosonicState.vacuum(2), 0.5, 0, 1)
    a = pnr_sample(state, modes=None, cutoff=10, rng=np.random.default_rng(0))
    b = pnr_sample(state, modes=None, cutoff=10, rng=np.random.default_rng(0))
    assert isinstance(a, tuple)
    assert len(a) == 2
    assert all(isinstance(x, int) for x in a)
    assert a == b
    # single-mode tuple sampling
    sa = pnr_sample(state, modes=(0,), cutoff=10, rng=np.random.default_rng(1))
    sb = pnr_sample(state, modes=(0,), cutoff=10, rng=np.random.default_rng(1))
    assert isinstance(sa, tuple) and len(sa) == 1
    assert sa == sb

def test_b10_pnr_sample_marginals_match_probs() -> None:
    # 1000 shots each mode; the empirical marginal of mode 0 should track pnr_probs.
    rng = np.random.default_rng(7)
    state = two_mode_squeeze(BosonicState.vacuum(2), 0.5, 0, 1)
    cutoff = 8
    n_shots = 2000
    counts = np.zeros(cutoff, dtype=float)
    for _ in range(n_shots):
        outcome = pnr_sample(state, modes=(0,), cutoff=cutoff, rng=rng)
        counts[outcome[0]] += 1.0
    empirical = counts / n_shots
    probs = pnr_probs(state, modes=(0,), cutoff=cutoff)
    probs = probs / probs.sum()
    np.testing.assert_allclose(empirical, probs, atol=5e-2)

# ---------------------------------------------------------------------------
# AC-6: GKP⊗GKP smoke (finite / non-negative / Σ ≤ 1+ε)
# ---------------------------------------------------------------------------

def test_b10_gkp_gkp_smoke() -> None:
    from cvsim.bosonic import gkp0

    # A two-mode GKP⊗GKP via two independent GKP states on separate modes.
    # Build a 2-mode product of gkp0 on mode 0 and gkp0 on mode 1 (block-diagonal
    # V, concatenated rbar). This is a non-Gaussian product with cross='full'
    # within each mode's comb.
    g0 = gkp0(0.1, grid_size=2, cross="full", lattice="2d")
    single = g0.components[0]
    mv = single.V.shape[0]
    # gkp0 is single-mode; embed into a 2-mode product with itself, using the
    # grouped xxpp layout [x0, x1, p0, p1]: mode j's (x,p) live at indices
    # [j, m+j]. Each single-mode component V is 2×2 [x,p]; the 2-mode block is
    # diag(V0, V1) but re-ordered to grouped — the production kernel slices
    # blk_indices=[0, 2, 1, 3], so we store grouped and let it re-slice.
    V2 = np.zeros((2 * mv, 2 * mv))
    # grouped [x0,x1,p0,p1]: put component 0's (x,p) block at indices {(0,2)}
    # and component 1's at {(1,3)}.
    V2[np.ix_([0, 2], [0, 2])] = single.V
    V2[np.ix_([1, 3], [1, 3])] = single.V
    comps: list[Component] = []
    for c1 in g0.components:
        for c2 in g0.components:
            rb = np.zeros(2 * mv, dtype=complex)
            # grouped: [x0, x1, p0, p1]
            rb[0] = c1.rbar[0]   # x0
            rb[1] = c2.rbar[0]   # x1
            rb[2] = c1.rbar[1]   # p0
            rb[3] = c2.rbar[1]   # p1
            comps.append(Component(V2.copy(), rb, complex(c1.w * c2.w)))
    state = BosonicState(comps)
    cutoff = 4
    p = pnr_probs(state, modes=None, cutoff=cutoff)
    assert p.dtype == np.float64
    assert np.all(np.isfinite(p))
    assert np.all(p >= 0.0)
    assert float(np.sum(p)) <= 1.0 + 1e-6

# ---------------------------------------------------------------------------
# AC-7: B9 single-mode regression (unchanged)
# ---------------------------------------------------------------------------

def test_b10_b9_single_mode_regression() -> None:
    alpha = 1.0
    cutoff = 8
    p = pnr_probs(coherent(alpha), cutoff=cutoff)
    expected = np.array(
        [np.exp(-alpha**2) * alpha ** (2 * n) / math.factorial(n) for n in range(cutoff)]
    )
    np.testing.assert_allclose(p, expected, atol=1e-10, rtol=1e-10)
    # TMSV single mode == thermal (B9 path, with empty modes sentinel)
    r = 0.5
    state = two_mode_squeeze(BosonicState.vacuum(2), r, 0, 1)
    p1 = pnr_probs(state, mode=0, cutoff=10)
    nbar = np.sinh(r) ** 2
    thermal = np.array([nbar**n / (1 + nbar) ** (n + 1) for n in range(10)])
    np.testing.assert_allclose(p1, thermal, atol=1e-6)
