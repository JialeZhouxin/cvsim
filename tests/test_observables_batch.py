"""F-SAMPLE batch (vision §4.2): vectorized homodyne/heterodyne/quadrature
sampling. Statistical convergence, seed reproducibility, R5 size=1
equivalence with the single-shot samplers, RNG-call count, guards."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import (
    GaussianState,
    heterodyne_sample,
    heterodyne_sample_batch,
    homodyne_mean,
    homodyne_sample,
    homodyne_sample_batch,
)


def test_homodyne_batch_size1_matches_single():
    """R5: same rng stream → batch(size=1) equals single-shot value."""
    st = GaussianState.squeezed(0.8, 0.3)
    r1, r2 = np.random.default_rng(5), np.random.default_rng(5)
    a = homodyne_sample(st, 0, 0.3, rng=r1)
    b = homodyne_sample_batch(st, 0, 0.3, size=1, rng=r2)
    assert b.shape == (1,)
    assert a == float(b[0])


def test_heterodyne_batch_size1_matches_single():
    st = GaussianState.squeezed(0.8, 0.3)
    r1, r2 = np.random.default_rng(6), np.random.default_rng(6)
    a = heterodyne_sample(st, rng=r1)
    b = heterodyne_sample_batch(st, size=1, rng=r2)
    assert b.shape == (1,)
    assert np.iscomplexobj(b)
    assert a == complex(b[0])


def test_homodyne_batch_statistics_converge():
    """Squeezed vacuum φ=0: μ=0, σ²=½e^{-2r}; N=1e5 within 3σ."""
    st = GaussianState.squeezed(1.0, 0.0)
    rng = np.random.default_rng(2)
    h = homodyne_sample_batch(st, phi=0.0, size=100_000, rng=rng)
    assert len(h) == 100_000
    expt_var = 0.5 * np.exp(-2.0)
    # 3σ of the sample-variance estimator ≈ 3·√(2/N)·σ²
    tol = 3 * np.sqrt(2 / 100_000) * expt_var
    assert abs(h.var() - expt_var) < tol
    assert abs(h.mean() - homodyne_mean(st, 0, 0.0)) < 3 * np.sqrt(expt_var / 100_000)


def test_heterodyne_batch_vacuum_statistics():
    """Vacuum heterodyne: ⟨β⟩=0, ⟨|β|²⟩=1 (Σ=V+I/2=I, β=(x+ip)/√2)."""
    st = GaussianState.vacuum(1)
    b = heterodyne_sample_batch(st, size=100_000, rng=np.random.default_rng(1))
    assert abs(b.real.mean()) < 0.01
    assert abs(b.imag.mean()) < 0.01
    assert abs((abs(b) ** 2).mean() - 1.0) < 0.03


def test_heterodyne_batch_coherent_shift():
    """Coherent α=1: ⟨β⟩ ≈ α."""
    st = GaussianState.coherent(1.0)
    b = heterodyne_sample_batch(st, size=100_000, rng=np.random.default_rng(8))
    assert abs(b.mean() - 1.0) < 0.03


def test_quadratures_batch_shape_and_statistics():
    """Whole-state xxpp draws: vacuum ⟨x²⟩=⟨p²⟩=½; squeezed x²=½e^{-2r}."""
    st = GaussianState.squeezed(1.0, 0.0)
    q = st.sample_quadratures(100_000, rng=np.random.default_rng(3))
    assert q.shape == (100_000, 2)
    assert abs(q[:, 0].var() - 0.5 * np.exp(-2.0)) < 0.003
    assert abs(q[:, 1].var() - 0.5 * np.exp(2.0)) < 0.05
    v = GaussianState.vacuum(1)
    qv = v.sample_quadratures(10_000, rng=np.random.default_rng(4))
    assert abs(qv[:, 0].var() - 0.5) < 0.03


def test_rng_accepts_generator_and_defaults():
    """rng= accepted; omitted rng → fresh entropy (not seeded, never crashes)."""
    st = GaussianState.vacuum(2)
    a = heterodyne_sample_batch(st, size=10, rng=np.random.default_rng(7))
    b = heterodyne_sample_batch(st, size=10, rng=np.random.default_rng(7))
    np.testing.assert_array_equal(a, b)
    assert len(heterodyne_sample_batch(st, size=10)) == 10


def test_seed_reproducibility_golden():
    """vision §7.3 golden: fixed seed → exact array (first 8 entries)."""
    st = GaussianState.squeezed(0.6, 0.0)
    h = homodyne_sample_batch(st, phi=0.0, size=8, rng=np.random.default_rng(1234))
    np.testing.assert_allclose(
        h,
        [
            -0.62239843,
            0.02487515,
            0.28751652,
            0.05922669,
            0.33519174,
            1.13048184,
            -0.57388466,
            0.36690821,
        ],
        atol=1e-8,
    )


def test_vectorized_single_rng_call():
    """R4: batch uses exactly one RNG call per function — count via a
    duck-typed wrapper (Generator methods are read-only C attrs)."""
    st = GaussianState.vacuum(2)
    calls = {"n": 0, "mvn": 0}
    inner = np.random.default_rng(0)

    class CountingRNG:
        def normal(self, *a, **k):
            calls["n"] += 1
            return inner.normal(*a, **k)

        def multivariate_normal(self, *a, **k):
            calls["mvn"] += 1
            return inner.multivariate_normal(*a, **k)

    homodyne_sample_batch(st, phi=0.0, size=500, rng=CountingRNG())
    heterodyne_sample_batch(st, size=500, rng=CountingRNG())
    st.sample_quadratures(500, rng=CountingRNG())
    assert calls == {"n": 1, "mvn": 2}


def test_size_validation():
    st = GaussianState.vacuum(1)
    for bad in (0, -3, 1.5, "3", True):
        with pytest.raises(ValueError, match="size"):
            homodyne_sample_batch(st, size=bad, rng=np.random.default_rng(0))
        with pytest.raises(ValueError, match="size"):
            heterodyne_sample_batch(st, size=bad, rng=np.random.default_rng(0))
        with pytest.raises(ValueError, match="size"):
            st.sample_quadratures(size=bad, rng=np.random.default_rng(0))


def test_homodyne_batch_singular_variance_rejected():
    """σ²→0 (strong x-squeeze) — same guard as the single-shot sampler."""
    st = GaussianState.squeezed(17.0, 0.0)  # ½e^{-34} < EPS
    with pytest.raises(ValueError, match="variance too small"):
        homodyne_sample_batch(st, phi=0.0, size=10, rng=np.random.default_rng(0))
    with pytest.raises(ValueError, match="variance too small"):
        homodyne_sample(st, 0, 0.0, rng=np.random.default_rng(0))


def test_heterodyne_batch_multi_mode_edge():
    """Edge marginal on mode 1 of a TMSV: Σ = V_1 + I/2 = (½cosh2r+½) I,
    so Var(Re β) = Σ_xx/2 (β scale 1/√2)."""
    st = GaussianState.tmsv(0.6)
    b = heterodyne_sample_batch(st, mode=1, size=100_000, rng=np.random.default_rng(9))
    expt_var = (np.cosh(2 * 0.6) + 1) / 4
    assert abs(b.real.var() - expt_var) < 3 * np.sqrt(2 / 100_000) * expt_var
