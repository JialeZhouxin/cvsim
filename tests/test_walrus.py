"""GBS adapter: export_cov_for_walrus format layer + thewalrus 对拍层.

Format layer runs without thewalrus; comparison layer skips via
``pytest.importorskip`` (PRD AC1/AC2).
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import GaussianState, export_cov_for_walrus

# --- format layer (no thewalrus needed) ---


def test_vacuum_export():
    m = 2
    sigma, mu = export_cov_for_walrus(GaussianState.vacuum(m))
    # hbar=2 normalization: vacuum sigma = I
    np.testing.assert_allclose(sigma, np.eye(2 * m), atol=1e-15)
    np.testing.assert_allclose(mu, 0.0, atol=1e-15)


def test_squeezed_diagonal():
    r = 1.0
    st = GaussianState.squeezed(r)
    sigma, mu = export_cov_for_walrus(st)
    # cvsim V = diag(e^{-2r}, e^{2r})/2 (xxpp, ħ=1) → sigma = 2V
    np.testing.assert_allclose(sigma, np.diag([np.exp(-2 * r), np.exp(2 * r)]), atol=1e-15)
    np.testing.assert_allclose(mu, 0.0, atol=1e-15)


def test_shape_and_symmetry():
    st = GaussianState.squeezed(0.7, phi=0.4)
    sigma, mu = export_cov_for_walrus(st)
    assert sigma.shape == (2, 2)
    assert mu.shape == (2,)
    np.testing.assert_allclose(sigma, sigma.T, atol=1e-15)


def test_mean_scaling_sf_quadratures():
    # thewalrus >= 0.20 uses xxpp like cvsim; mu = sqrt(2)*rbar (SF quads)
    a1, a2 = 0.5 + 0.3j, -0.2 + 0.8j
    st = GaussianState.product(GaussianState.coherent(a1), GaussianState.coherent(a2))
    sigma, mu = export_cov_for_walrus(st)
    assert sigma.shape == (4, 4)
    np.testing.assert_allclose(sigma, np.eye(4), atol=1e-15)  # coherent: V=I/2
    np.testing.assert_allclose(
        mu,
        [2 * a1.real, 2 * a2.real, 2 * a1.imag, 2 * a2.imag],  # xxpp order
        atol=1e-15,
    )


def test_xxpp_cov_blocks():
    # two thermal modes, different nbar: sigma stays xxpp (q1,q2,p1,p2)
    st = GaussianState.product(GaussianState.thermal(0.3), GaussianState.thermal(1.7))
    sigma, _ = export_cov_for_walrus(st)
    expected = np.diag([1.6, 4.4, 1.6, 4.4])  # (2nbar+1) per mode, xxpp
    np.testing.assert_allclose(sigma, expected, atol=1e-15)


def test_export_errors():
    with pytest.raises(TypeError):
        export_cov_for_walrus(np.eye(2))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        export_cov_for_walrus("vacuum")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        # GaussianState rejects bad shapes at construction; keep the
        # defensive path covered via a state with a mutated V.
        st = GaussianState.vacuum(1)
        st.V = np.ones((3, 3))
        export_cov_for_walrus(st)


def test_no_aliasing():
    st = GaussianState.squeezed(0.5)
    sigma, mu = export_cov_for_walrus(st)
    sigma[0, 0] = -99.0
    mu[0] = -99.0
    np.testing.assert_allclose(st.V[0, 0], 0.5 * np.exp(-1.0), atol=1e-15)
    np.testing.assert_allclose(st.rbar[0], 0.0, atol=1e-15)


# --- comparison layer (needs thewalrus, cvsim[gbs]) ---


def _squeezed_vac_p(n: int, r: float) -> float:
    """Analytic P(2n) for single-mode squeezed vacuum: sech(r)·(2n)!/(2ⁿn!)²·tanh²ⁿ(r)."""
    from math import factorial

    return (
        (1.0 / np.cosh(r)) * (factorial(2 * n) / (2**n * factorial(n)) ** 2) * np.tanh(r) ** (2 * n)
    )


def test_walrus_squeezed_pn():
    thewalrus = pytest.importorskip("thewalrus", exc_type=ImportError)
    from thewalrus.quantum import density_matrix

    r = 1.0
    sigma, mu = export_cov_for_walrus(GaussianState.squeezed(r))
    dm = density_matrix(mu, sigma, cutoff=6, hbar=2)
    for n in (0, 1, 2):  # dm[2n, 2n] = P(2n)
        got = np.real(dm[2 * n, 2 * n])
        expected = _squeezed_vac_p(n, r)
        assert abs(got - expected) < 1e-9, f"P({2 * n}) = {got}, expected {expected}"
    # odd diagonal vanish
    assert abs(np.real(dm[1, 1])) < 1e-9
    assert abs(np.real(dm[3, 3])) < 1e-9


def test_walrus_coherent_poisson():
    thewalrus = pytest.importorskip("thewalrus", exc_type=ImportError)
    from thewalrus.quantum import density_matrix

    alpha = 0.5 + 0.0j
    sigma, mu = export_cov_for_walrus(GaussianState.coherent(alpha))
    dm = density_matrix(mu, sigma, cutoff=5, hbar=2)
    # P(n) = e^{-|α|²}|α|^{2n}/n!
    from math import factorial

    for n in (0, 1):
        expected = np.exp(-(abs(alpha) ** 2)) * abs(alpha) ** (2 * n) / factorial(n)
        assert abs(np.real(dm[n, n]) - expected) < 1e-9


def test_walrus_tmsv_ordering_xxpp():
    """Ordering-sensitive cross-check: thewalrus >= 0.20 quantum module
    reads xxpp blocks (its docstring says xp-ordering — stale). TMSV
    correlated P(n,n) only matches if the export keeps xxpp order."""
    thewalrus = pytest.importorskip("thewalrus", exc_type=ImportError)
    from thewalrus.quantum import density_matrix

    r = 0.5
    st = GaussianState.tmsv(r)
    sigma, mu = export_cov_for_walrus(st)
    dm = density_matrix(mu, sigma, cutoff=5, hbar=2)
    # |TMSV⟩ = sech r Σ tanhⁿ r |n,n⟩ → P(n,n) = sech²r tanh^{2n}r
    for n in (0, 1, 2):
        expected = (1.0 / np.cosh(r) ** 2) * np.tanh(r) ** (2 * n)
        got = np.real(dm[n, n, n, n])
        assert abs(got - expected) < 1e-9, f"P({n},{n}) = {got}, expected {expected}"
