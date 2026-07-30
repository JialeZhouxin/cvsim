"""Heterodyne: mean / cov / sample / condition / circuit."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import (
    GaussianCircuit,
    GaussianState,
    heterodyne_condition,
    heterodyne_cov_xp,
    heterodyne_mean,
    heterodyne_sample,
    heterodyne_sample_and_condition,
    purity,
    symplectic_eigenvalues,
)

ATOL = 1e-10


def test_heterodyne_vacuum_mean_cov():
    st = GaussianState.vacuum(1)
    assert abs(heterodyne_mean(st, 0)) < ATOL
    assert np.allclose(heterodyne_cov_xp(st, 0), np.eye(2), atol=ATOL)


def test_heterodyne_coherent_mean_is_alpha():
    alpha = 0.7 + 0.3j
    st = GaussianState.coherent(alpha, nmode=1)
    assert heterodyne_mean(st, 0) == pytest.approx(alpha, abs=ATOL)
    assert np.allclose(heterodyne_cov_xp(st, 0), np.eye(2), atol=ATOL)


@pytest.mark.parametrize("nbar", [0.0, 0.5, 1.0, 2.0])
def test_heterodyne_thermal_cov(nbar):
    st = GaussianState.thermal(nbar, nmode=1)
    # Σ = V + I/2 = (nbar + 1/2)I + (1/2)I = (nbar+1) I
    expect = (nbar + 1.0) * np.eye(2)
    assert np.allclose(heterodyne_cov_xp(st, 0), expect, atol=ATOL)


def test_heterodyne_sample_mc_vacuum():
    st = GaussianState.vacuum(1)
    rng = np.random.default_rng(42)
    samples = np.array(
        [heterodyne_sample(st, 0, rng=rng) for _ in range(4000)],
        dtype=complex,
    )
    assert abs(samples.mean()) < 0.05
    # Var(Re β)=Var(Im β)=1/2 for vacuum (Σ_xp=I → var x=1 → var Reβ = var(x/√2)=1/2)
    assert samples.real.var() == pytest.approx(0.5, abs=0.05)
    assert samples.imag.var() == pytest.approx(0.5, abs=0.05)


def test_heterodyne_condition_removes_mode():
    st = GaussianState.coherent(0.5 + 0.1j, nmode=1)
    out = heterodyne_condition(st, 0, 0.5 + 0.1j)
    assert out.nmode == 0
    assert out.V.shape == (0, 0)


def test_heterodyne_condition_uncorrelated_product():
    a = GaussianState.thermal(0.5, nmode=1)
    b = GaussianState.thermal(1.0, nmode=1)
    prod = GaussianState.product(a, b)
    red = heterodyne_condition(prod, 0, 0.0)
    assert red.nmode == 1
    assert np.allclose(red.V, b.V, atol=ATOL)
    assert np.allclose(red.rbar, b.rbar, atol=ATOL)


def test_heterodyne_condition_three_mode_pack_order():
    """Measure middle mode; remaining coherents keep displacements in xxpp."""
    a = GaussianState.coherent(0.5 + 0j, nmode=1)
    b = GaussianState.thermal(0.3, nmode=1)
    c = GaussianState.coherent(0.2j, nmode=1)
    st = GaussianState.product(a, b, c)
    red = heterodyne_condition(st, 1, 0.0)
    assert red.nmode == 2
    assert red.rbar[0] == pytest.approx(np.sqrt(2) * 0.5, abs=ATOL)
    assert red.rbar[3] == pytest.approx(np.sqrt(2) * 0.2, abs=ATOL)
    assert abs(red.rbar[1]) < ATOL and abs(red.rbar[2]) < ATOL
    assert np.allclose(red.V, 0.5 * np.eye(4), atol=ATOL)


def test_heterodyne_tmsv_steers_to_coherent():
    """TMSV: hetero on A with β leaves B pure coherent |tanh(r) β*⟩.

    p-quadratures are anti-correlated in the standard TMSV CM, so the
    steered amplitude is the complex conjugate (phase-sensitive EPR).
    """
    r = 0.6
    beta = 0.4 + 0.2j
    tm = GaussianState.tmsv(r, nmode=2, mode1=0, mode2=1)
    red = heterodyne_condition(tm, 0, beta)
    assert red.nmode == 1
    assert purity(red) == pytest.approx(1.0, abs=1e-9)
    assert symplectic_eigenvalues(red)[0] == pytest.approx(0.5, abs=1e-9)
    # vacuum cov (coherent)
    assert np.allclose(red.V, 0.5 * np.eye(2), atol=1e-9)
    beta_B = complex((red.rbar[0] + 1j * red.rbar[1]) / np.sqrt(2.0))
    expect = np.tanh(r) * np.conjugate(beta)
    assert beta_B == pytest.approx(expect, abs=1e-9)


def test_heterodyne_sample_and_condition_combo():
    st = GaussianState.tmsv(0.5, nmode=2)
    rng = np.random.default_rng(1)
    beta, red = heterodyne_sample_and_condition(st, mode=0, rng=rng)
    assert isinstance(beta, complex)
    assert red.nmode == 1
    assert purity(red) == pytest.approx(1.0, abs=1e-8)


def test_heterodyne_bad_mode():
    st = GaussianState.vacuum(1)
    with pytest.raises(IndexError):
        heterodyne_mean(st, 3)


def test_circuit_measure_heterodyne():
    rng = np.random.default_rng(0)
    circ = (
        GaussianCircuit(2)
        .displace(0, 0.5 + 0.0j)
        .measure_heterodyne(0, "h0")
    )
    st, results = circ.run(rng=rng)
    assert "h0" in results
    assert isinstance(results["h0"], complex)
    assert st.nmode == 1
    # remaining mode was vacuum
    assert np.allclose(st.V, 0.5 * np.eye(2), atol=ATOL)
