"""B3+ Bosonic heterodyne exactification (ADR-0007): 2D Q-surface + sequential CDF inversion.

Oracles:
1. even/odd cat closed-form Q (cross-term fringes), atol 1e-7
   Q±(β) = e^{−|β|²−α²}|2cosh(αβ*)|² / (πN±)   (even)
   Q±(β) = e^{−|β|²−α²}|2sinh(αβ*)|² / (πN±)   (odd),  N± = 2(1±e^{−2α²})
2. ∫Q d²β = 1 (grid integral, d²β = dx dp / 2)
3. consistency: Σ_β Q(β)·w_k^post(β) d²β = w_k^orig (conditioning likelihood)
4. sampling histogram vs Q grid (bin-level z-score)
5. K=1 reconciliation unchanged (test_b1 suite stays green)
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import (
    BosonicState,
    coherent,
    even_cat,
    heterodyne_condition,
    heterodyne_pdf,
    heterodyne_sample,
    odd_cat,
    weight_sum,
)

pytestmark = pytest.mark.phaseB3


def _cat_q_closed_form(alpha: float, beta: complex, even: bool) -> float:
    """Husimi Q of |cat±⟩ = (|α⟩ ± |−α⟩)/√N±, α real (see module docstring)."""
    ov = np.exp(-2.0 * alpha**2)
    sign = 1.0 if even else -1.0
    norm = 2.0 * (1.0 + sign * ov)
    z = alpha * np.conj(complex(beta))
    core = 2.0 * (np.cosh(z) if even else np.sinh(z))
    return float(np.exp(-(abs(beta) ** 2) - alpha**2) * abs(core) ** 2 / (np.pi * norm))


class TestCatQClosedForm:
    """Oracle 1: Q grid matches closed form on cat states (cross terms live)."""

    @pytest.mark.parametrize("alpha", [0.8, 1.5])
    @pytest.mark.parametrize("even", [True, False])
    def test_pdf_matches_closed_form(self, alpha: float, even: bool) -> None:
        state = even_cat(alpha) if even else odd_cat(alpha)
        xs, ps, Q = heterodyne_pdf(state, mode=0)
        assert Q.shape == (xs.size, ps.size)
        for i, x in enumerate(xs):
            for j, p in enumerate(ps):
                beta = (x + 1j * p) / np.sqrt(2.0)
                np.testing.assert_allclose(
                    Q[i, j], _cat_q_closed_form(alpha, beta, even), atol=1e-7
                )

    def test_fringes_present(self) -> None:
        """Odd cat: node at origin; even cat: bright fringe at origin."""
        xs, ps, Qe = heterodyne_pdf(even_cat(1.2), mode=0)
        _, _, Qo = heterodyne_pdf(odd_cat(1.2), mode=0)
        ix = int(np.argmin(np.abs(xs)))
        ip = int(np.argmin(np.abs(ps)))
        assert Qo[ix, ip] < 1e-6  # node at origin for odd cat
        assert Qe[ix, ip] > 0.05  # bright fringe at origin for even cat


class TestNormalization:
    """Oracle 2: ∫Q d²β = 1."""

    @pytest.mark.parametrize(
        "make_state",
        [lambda: even_cat(1.0), lambda: odd_cat(1.0), lambda: coherent(0.6 + 0.2j)],
    )
    def test_grid_integral_is_one(self, make_state) -> None:
        xs, ps, Q = heterodyne_pdf(make_state(), mode=0)
        dx = xs[1] - xs[0]
        dp = ps[1] - ps[0]
        # d²β = dx dp / 2; tolerance 1e-5 — residual is the physical tail
        # beyond the ±6σ grid (grid truncation, not a normalisation bug)
        total = float(np.sum(Q) * dx * dp / 2.0)
        np.testing.assert_allclose(total, 1.0, atol=1e-5)


class TestConditioning:
    """Oracle 3: Σ_β Q(β)·w_k^post(β) d²β = w_k^orig over a coarse grid."""

    def test_consistency_identity_two_mode(self) -> None:
        """even_cat ⊗ vacuum; condition mode 0; component-0 posterior weight
        integrated against Q(β) recovers the original diagonal weight."""
        from cvsim.bosonic.state import tensor_product

        alpha = 0.8
        cat = even_cat(alpha)
        vac = BosonicState.vacuum(1)
        rho = tensor_product([cat, vac])

        xs, ps, Q = heterodyne_pdf(cat, mode=0)
        dx = xs[1] - xs[0]
        dp = ps[1] - ps[0]
        acc = 0.0 + 0.0j
        # coarse grid for speed; fringes undersampled → tolerance 2e-2
        step = 4
        for i in range(0, len(xs), step):
            for j in range(0, len(ps), step):
                if Q[i, j] <= 1e-12:
                    continue  # zero-mass corners: conditioning refuses (honest)
                beta = (xs[i] + 1j * ps[j]) / np.sqrt(2.0)
                post = heterodyne_condition(rho, 0, beta)
                acc += Q[i, j] * post.components[0].w * (dx * step) * (dp * step) / 2.0
        ov = np.exp(-2.0 * alpha**2)
        w_diag = 1.0 / (2.0 * (1.0 + ov))
        np.testing.assert_allclose(acc.real, w_diag, atol=2e-2)
        assert abs(acc.imag) < 1e-9


class TestSampling:
    """Oracle 4: histogram vs Q closed form, bin-level z-score."""

    def test_histogram_matches_q(self) -> None:
        alpha = 1.2
        state = even_cat(alpha)
        rng = np.random.default_rng(42)
        n = 20_000
        betas = np.array([heterodyne_sample(state, mode=0, rng=rng) for _ in range(n)])
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


class TestK1Degenerate:
    """K=1 keeps exact Gaussian semantics (statistics, not stream)."""

    def test_coherent_statistics(self) -> None:
        alpha = 0.8 + 0.4j
        bs = coherent(alpha)
        rng = np.random.default_rng(17)
        n = 4000
        draws = np.array([heterodyne_sample(bs, rng=rng) for _ in range(n)])
        tol = 3.0 / np.sqrt(n)
        assert abs(complex(draws.mean()) - alpha) < tol + 1e-3
        assert abs(np.var(draws.real) - 0.5) < 0.1
        assert abs(np.var(draws.imag) - 0.5) < 0.1

    def test_condition_k1_matches_gaussian(self) -> None:
        from cvsim.gaussian.gates import beamsplitter
        from cvsim.gaussian.observables import (
            heterodyne_condition as g_cond,
        )
        from cvsim.gaussian.state import GaussianState
        from cvsim.symplectic import d_displace

        gs = GaussianState.squeezed(0.5, nmode=2, mode=1)
        gs = GaussianState(V=gs.V, rbar=gs.rbar + d_displace(2, 0.4 + 0.3j, 1))
        gs = beamsplitter(gs, 0, 1, 0.3)
        bs = BosonicState.from_gaussian(gs)
        out = heterodyne_condition(bs, 1, 0.6 - 0.2j)
        ref = g_cond(gs, 1, 0.6 - 0.2j)
        c = out.components[0]
        np.testing.assert_allclose(c.V, ref.V, atol=1e-10)
        np.testing.assert_allclose(c.rbar, ref.rbar, atol=1e-10)
        assert abs(c.w - 1.0) < 1e-12
        assert abs(weight_sum(out) - 1.0) < 1e-12
