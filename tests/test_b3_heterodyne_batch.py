"""B3 batch extension (ADR-0007 appendix): heterodyne_sample_batch.

One grid build amortised over N iid outcome-only shots — the piecewise-
constant density is sampled by a single flattened-CDF inversion (row-offset
trick), so the distribution is bin-identical to the sequential per-shot
sampler. Tests: bin-level histogram vs Q closed form (mirror of
TestSampling), size=1 rng-stream equivalence, seed reproducibility,
statistical convergence, size validation, zero-mass-row honesty.
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import (
    coherent,
    even_cat,
    heterodyne_pdf,
    heterodyne_sample,
    heterodyne_sample_batch,
)


def _cat_q_closed_form(alpha: float, beta: complex, even: bool) -> float:
    """Husimi Q of |cat±> = (|alpha> ± |-alpha>)/sqrt(N), alpha real.

    Mirrors tests/test_b3_heterodyne_exact.py (z = alpha*conj(beta), |core|^2
    form) — do not substitute an algebraically-equivalent-looking rewrite:
    the |cosh|² expansion differs for complex beta and broke bin-level z.
    """
    ov = np.exp(-2.0 * alpha**2)
    sign = 1.0 if even else -1.0
    norm = 2.0 * (1.0 + sign * ov)
    z = alpha * np.conj(complex(beta))
    core = 2.0 * (np.cosh(z) if even else np.sinh(z))
    return float(np.exp(-(abs(beta) ** 2) - alpha**2) * abs(core) ** 2 / (np.pi * norm))


class TestBatchSampling:
    def test_histogram_matches_q(self) -> None:
        """Oracle 4 mirror: batch draws vs cat closed form, bin-level z."""
        alpha = 1.2
        state = even_cat(alpha)
        rng = np.random.default_rng(42)
        n = 20_000
        betas = heterodyne_sample_batch(state, mode=0, size=n, rng=rng)
        assert betas.shape == (n,)
        assert np.iscomplexobj(betas)
        xs_s = np.sqrt(2.0) * betas.real
        ps_s = np.sqrt(2.0) * betas.imag

        edges_x = np.linspace(-3.5, 3.5, 15)
        edges_p = np.linspace(-3.5, 3.5, 15)
        H, _, _ = np.histogram2d(xs_s, ps_s, bins=[edges_x, edges_p])
        ctr_x = 0.5 * (edges_x[:-1] + edges_x[1:])
        ctr_p = 0.5 * (edges_p[:-1] + edges_p[1:])
        exp = np.zeros_like(H, dtype=float)
        for i, xc in enumerate(ctr_x):
            for j, pc in enumerate(ctr_p):
                beta = (xc + 1j * pc) / np.sqrt(2.0)
                exp[i, j] = _cat_q_closed_form(alpha, beta, True) * (
                    (edges_x[1] - edges_x[0]) * (edges_p[1] - edges_p[0]) / 2.0
                )
        p_obs = H / n
        sigma = np.sqrt(np.maximum(exp, 1e-12) * (1 - np.minimum(exp, 1e-12)) / n)
        mask = exp > 1e-4
        assert mask.sum() >= 20
        z = np.abs(p_obs - exp) / np.where(mask, sigma, 1.0)
        assert np.all(z[mask] < 6.0), f"max |z| = {z[mask].max():.2f}"

    def test_size1_matches_single(self) -> None:
        """Same rng stream: batch(size=1) equals the single-shot value."""
        state = even_cat(1.0)
        r1, r2 = np.random.default_rng(5), np.random.default_rng(5)
        a = heterodyne_sample(state, mode=0, rng=r1)
        b = heterodyne_sample_batch(state, mode=0, size=1, rng=r2)
        assert b.shape == (1,)
        assert a == complex(b[0])

    def test_seed_reproducible(self) -> None:
        state = coherent(0.8 + 0.4j)
        b1 = heterodyne_sample_batch(state, size=100, rng=np.random.default_rng(7))
        b2 = heterodyne_sample_batch(state, size=100, rng=np.random.default_rng(7))
        np.testing.assert_array_equal(b1, b2)

    def test_coherent_statistics(self) -> None:
        """K=1: ⟨β⟩ ≈ α, ⟨|β|²⟩ = |α|² + 1."""
        alpha = 0.8 + 0.4j
        st = coherent(alpha)
        n = 40_000
        b = heterodyne_sample_batch(st, size=n, rng=np.random.default_rng(3))
        assert abs(complex(b.mean()) - alpha) < 3.0 / np.sqrt(n) + 1e-3
        assert abs((abs(b) ** 2).mean() - (abs(alpha) ** 2 + 1.0)) < 0.03

    def test_size_validation(self) -> None:
        st = coherent(0.5)
        for bad in (0, -3, 1.5, "3", True):
            with pytest.raises(ValueError, match="size"):
                heterodyne_sample_batch(st, size=bad, rng=np.random.default_rng(0))

    def test_n_grid_lim_passthrough(self) -> None:
        """Explicit grid override reaches the same CDF machinery."""
        state = coherent(0.3)
        xs1, ps1, Q1 = heterodyne_pdf(state, 0, n_grid=41, lim=2.0)
        assert xs1.size == 41
        b = heterodyne_sample_batch(
            state, size=200, n_grid=41, lim=2.0, rng=np.random.default_rng(1)
        )
        assert b.shape == (200,)
        # coherent(0.3): x,p ∈ [-2,2] + jitter → |β|√2 = √(x²+p²) ≤ 2√2
        assert np.all(np.abs(b) * np.sqrt(2.0) <= np.sqrt(8.0) + 1e-9)

    def test_all_zero_row_honest_error(self) -> None:
        """Q mass numerically underflows every grid point (α=30 coherent on
        a far grid) → honest "integrates to ~0" raise, not a fabricated
        sample from a zero CDF."""
        state = coherent(30.0)
        with pytest.raises(ValueError, match="integrates to ~0"):
            heterodyne_sample_batch(
                state, size=10, n_grid=5, lim=0.01, rng=np.random.default_rng(0)
            )
