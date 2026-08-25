"""B1 Bosonic measures: heterodyne (teaching cut) + threshold outcome-only."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import (
    BosonicState,
    coherent,
    even_cat,
    heterodyne_condition,
    heterodyne_sample,
    heterodyne_sample_and_condition,
    p_click,
    sample_threshold,
    weight_sum,
)
from cvsim.gaussian import GaussianState
from cvsim.gaussian.observables import heterodyne_condition as g_het_cond
from cvsim.gaussian.observables import heterodyne_sample as g_het_sample
from cvsim.gaussian.observables import p_click as g_p_click
from cvsim.gaussian.observables import sample_threshold as g_sample_threshold
from cvsim.symplectic import d_displace

pytestmark = pytest.mark.phaseB1


# ---------------------------------------------------------------------------
# threshold
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("alpha", [0.0, 0.3, 0.7 + 0.2j, 1.2j, 1.5])
def test_threshold_p_click_k1_matches_gaussian(alpha):
    gs = GaussianState.vacuum(1)
    gs = GaussianState(V=gs.V, rbar=gs.rbar + d_displace(1, alpha, 0))
    bs = coherent(alpha)
    np.testing.assert_allclose(p_click(bs), g_p_click(gs), atol=1e-10)


def test_threshold_p_click_mixed_state_cat():
    alpha = 0.8
    p = p_click(even_cat(alpha))
    assert 0.0 <= p <= 1.0
    # analytic: p_click = 1 − 1/cosh(α²) for |cat+⟩ (exercises complex r̄ terms)
    np.testing.assert_allclose(p, 1.0 - 1.0 / np.cosh(alpha**2), atol=1e-10)


def test_threshold_p_click_internal_sum_is_real():
    """Weighted vacuum overlap Σ w_k P0_k must be real (imag tolerance path)."""
    total = 0.0 + 0.0j
    for c in even_cat(0.8).components:
        V = c.V
        i = 0
        V1 = np.array([[V[i, i], V[i, 1]], [V[1, i], V[1, 1]]])
        r1 = np.array([c.rbar[i], c.rbar[1]])
        A = V1 + 0.5 * np.eye(2)
        total += (
            c.w * np.exp(-0.5 * complex(r1 @ np.linalg.solve(A, r1))) / np.sqrt(np.linalg.det(A))
        )
    assert abs(total.imag) < 1e-8
    assert abs(total.real - 1.0 / np.cosh(0.8**2)) < 1e-10


def test_threshold_sample_seeded_bernoulli():
    bs = coherent(0.7 + 0.2j)
    p = p_click(bs)
    rng = np.random.default_rng(3)
    n = 4000
    clicks = sum(sample_threshold(bs, rng=rng) for _ in range(n))
    # binomial: mean np, std √(np(1−p)) → |freq − p| < 5σ
    sigma = np.sqrt(p * (1.0 - p) / n)
    assert abs(clicks / n - p) < 5 * sigma
    # same seed as Gaussian sampler → identical outcome stream for K=1
    rng1 = np.random.default_rng(11)
    rng2 = np.random.default_rng(11)
    o1 = [sample_threshold(bs, rng=rng1) for _ in range(20)]
    gs = GaussianState(V=bs.components[0].V, rbar=bs.components[0].rbar.real)
    o2 = [g_sample_threshold(gs, rng=rng2) for _ in range(20)]
    assert o1 == o2


# ---------------------------------------------------------------------------
# heterodyne condition
# ---------------------------------------------------------------------------


def _g_2mode_correlated() -> GaussianState:
    """2-mode state with inter-mode correlations (squeeze + BS)."""
    from cvsim.gaussian.gates import beamsplitter

    gs = GaussianState.squeezed(0.5, nmode=2, mode=1)
    gs = GaussianState(V=gs.V, rbar=gs.rbar + d_displace(2, 0.4 + 0.3j, 1))
    return beamsplitter(gs, 0, 1, 0.3)


@pytest.mark.parametrize("beta", [0.6 - 0.2j, -0.3 + 0.1j, 1.0j])
def test_heterodyne_condition_k1_matches_gaussian(beta):
    gs = _g_2mode_correlated()
    bs = BosonicState.from_gaussian(gs)
    out = heterodyne_condition(bs, 1, beta)
    ref = g_het_cond(gs, 1, beta)
    assert out.n_components == 1
    c = out.components[0]
    np.testing.assert_allclose(c.V, ref.V, atol=1e-10)
    np.testing.assert_allclose(c.rbar, ref.rbar, atol=1e-10)
    assert abs(c.w - 1.0) < 1e-12
    assert abs(weight_sum(out) - 1.0) < 1e-12


def test_heterodyne_condition_single_mode_k1_zero_mode():
    bs = coherent(0.8 + 0.1j)
    out = heterodyne_condition(bs, 0, 0.5 + 0.2j)
    assert out.nmode == 0
    assert abs(weight_sum(out) - 1.0) < 1e-12


def test_heterodyne_condition_mixed_state_renormalizes():
    """even_cat (teaching pool = 2 diag peaks) keeps Σw = 1 after condition."""
    out = heterodyne_condition(even_cat(0.8), 0, 0.3 + 0.1j)
    assert out.nmode == 0
    assert abs(weight_sum(out) - 1.0) < 1e-12


def test_heterodyne_condition_outcome_forms():
    """complex / (x,p) array outcome forms agree."""
    bs = BosonicState.from_gaussian(_g_2mode_correlated())
    r1 = heterodyne_condition(bs, 1, 0.6 - 0.2j)
    xp = np.array([np.sqrt(2) * 0.6, -np.sqrt(2) * 0.2])
    r2 = heterodyne_condition(bs, 1, xp)
    np.testing.assert_allclose(r1.components[0].V, r2.components[0].V, atol=1e-12)
    np.testing.assert_allclose(r1.components[0].rbar, r2.components[0].rbar, atol=1e-12)


# ---------------------------------------------------------------------------
# heterodyne sample
# ---------------------------------------------------------------------------


def test_heterodyne_sample_k1_matches_gaussian_stream():
    """Same-seed K=1 sample: identical (single pool component, same RNG path)."""
    gs = _g_2mode_correlated()
    bs = BosonicState.from_gaussian(gs)
    rng1 = np.random.default_rng(5)
    rng2 = np.random.default_rng(5)
    for _ in range(10):
        o1 = heterodyne_sample(bs, 1, rng=rng1)
        o2 = g_het_sample(gs, 1, rng=rng2)
        assert o1 == o2


def test_heterodyne_sample_coherent_statistics():
    """K=1 coherent: sample mean ≈ α within 3σ/√N; per-quadrature var ≈ ½."""
    alpha = 0.8 + 0.4j
    bs = coherent(alpha)
    rng = np.random.default_rng(17)
    n = 4000
    draws = np.array([heterodyne_sample(bs, rng=rng) for _ in range(n)])
    mean = complex(draws.mean())
    tol = 3.0 / np.sqrt(n)  # σ=1/√2 per quadrature → 3σ/√N < tol
    assert abs(mean - alpha) < tol + 1e-3
    # β = (x + i p)/√2 with vacuum edge Σ = I → Var(Re β) = Var(Im β) = ½
    assert abs(np.var(draws.real) - 0.5) < 0.1
    assert abs(np.var(draws.imag) - 0.5) < 0.1


def test_heterodyne_sample_and_condition_consistent():
    bs = BosonicState.from_gaussian(_g_2mode_correlated())
    rng = np.random.default_rng(9)
    beta, out = heterodyne_sample_and_condition(bs, 1, rng=rng)
    ref = heterodyne_condition(bs, 1, beta)
    np.testing.assert_allclose(out.components[0].V, ref.components[0].V, atol=1e-12)
    assert abs(weight_sum(out) - 1.0) < 1e-12
