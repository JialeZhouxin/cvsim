"""F2 analyse: entropy_vn / log_negativity / fidelity / partial_trace."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.fock import FockDensity, FockState
from cvsim.fock.analyse import (
    entropy_vn,
    fidelity,
    log_negativity,
    partial_trace,
)
from cvsim.fock.gates import two_mode_squeeze
from cvsim.gaussian import GaussianState
from cvsim.gaussian.analyse import log_negativity as g_log_neg
from cvsim.gaussian.gates import two_mode_squeeze as g_tms

# -- entropy_vn --------------------------------------------------------------


def test_entropy_vn_pure_zero() -> None:
    assert entropy_vn(FockState.vacuum(10)) == pytest.approx(0.0, abs=1e-12)
    assert entropy_vn(FockState.coherent(14, 1.0)) == pytest.approx(0.0, abs=1e-12)
    assert entropy_vn(FockState.cat(12, 1.2)) == pytest.approx(0.0, abs=1e-12)


def test_entropy_vn_thermal_closed_form() -> None:
    nbar = 1.0
    d = FockDensity.thermal(40, nbar)
    s = entropy_vn(d)
    expected = (nbar + 1.0) * np.log(nbar + 1.0) - nbar * np.log(nbar)
    assert s == pytest.approx(expected, abs=1e-4)


def test_entropy_vn_maximally_mixed() -> None:
    N = 6
    rho = np.eye(N, dtype=complex) / N
    d = FockDensity(rho=rho, nmode=1)
    assert entropy_vn(d) == pytest.approx(np.log(N), abs=1e-12)


# -- partial_trace -----------------------------------------------------------


def test_partial_trace_pure_product() -> None:
    st = FockState.fock2(1, 2, 10)
    out = partial_trace(st, 0)
    np.testing.assert_allclose(out.rho, FockDensity.from_pure(FockState.fock(2, 10)).rho, atol=1e-12)
    out1 = partial_trace(st, 1)
    np.testing.assert_allclose(out1.rho, FockDensity.from_pure(FockState.fock(1, 10)).rho, atol=1e-12)


def test_partial_trace_density_product() -> None:
    d = FockDensity.from_pure(FockState.fock2(1, 2, 8))
    out = partial_trace(d, 0)
    ref = FockDensity.from_pure(FockState.fock(2, 8))
    np.testing.assert_allclose(out.rho, ref.rho, atol=1e-12)
    out1 = partial_trace(d, 1)
    ref1 = FockDensity.from_pure(FockState.fock(1, 8))
    np.testing.assert_allclose(out1.rho, ref1.rho, atol=1e-12)


def test_partial_trace_keep_both_identity() -> None:
    st = FockState.fock2(0, 1, 6)
    assert partial_trace(st, [0, 1]) is st
    with pytest.raises(IndexError):
        partial_trace(st, 2)


def test_partial_trace_entangled_tms_thermal_marginal() -> None:
    r = 0.5
    st = two_mode_squeeze(FockState.vacuum(18, nmode=2), r)
    out = partial_trace(st, 0)
    nbar = np.sinh(r) ** 2
    ref = FockDensity.thermal(18, nbar)
    np.testing.assert_allclose(np.real(np.diag(out.rho)), np.diag(ref.rho), atol=1e-8)
    d = partial_trace(FockDensity.from_pure(st), 0)
    np.testing.assert_allclose(d.rho, out.rho, atol=1e-12)


# -- log_negativity ----------------------------------------------------------


def test_log_neg_zero_for_product() -> None:
    st = FockState.fock2(1, 1, 8)
    assert log_negativity(st, 0) == pytest.approx(0.0, abs=1e-10)
    assert log_negativity(st, 1) == pytest.approx(0.0, abs=1e-10)


def test_log_neg_tms_matches_gaussian() -> None:
    """Fock numerical E_N vs Gaussian closed form (same TMS parameters)."""
    r = 0.4
    st = two_mode_squeeze(FockState.vacuum(20, nmode=2), r)
    fock_neg = log_negativity(st, 0)
    g = g_tms(GaussianState.vacuum(2), r, 0, 1)
    gauss_neg = g_log_neg(g, 0)
    # Fock E_N in nats, Gaussian in bits: E_N(TMS) = 2r (nats)
    assert fock_neg == pytest.approx(gauss_neg * np.log(2.0), abs=1e-3)


def test_log_neg_density_path() -> None:
    r = 0.3
    st = two_mode_squeeze(FockState.vacuum(16, nmode=2), r)
    d = FockDensity.from_pure(st)
    assert log_negativity(d, 1) == pytest.approx(log_negativity(st, 1), abs=1e-8)


def test_log_neg_validation() -> None:
    st = FockState.fock2(0, 1, 6)
    with pytest.raises(NotImplementedError):
        log_negativity(FockState.vacuum(6), 0)  # 1-mode
    with pytest.raises(IndexError):
        log_negativity(st, 2)


# -- fidelity ----------------------------------------------------------------


def test_fidelity_coherent_closed_form() -> None:
    """F(|α⟩,|β⟩) = e^{−|α−β|²} (truncation-corrected: amps renormalized)."""
    alpha = 1.0 + 0.0j
    beta = 0.5 + 0.3j
    st_a = FockState.coherent(25, alpha)
    st_b = FockState.coherent(25, beta)
    f = fidelity(st_a, st_b)
    expected = np.exp(-abs(alpha - beta) ** 2)
    assert f == pytest.approx(expected, abs=1e-3)


def test_fidelity_self_one() -> None:
    st = FockState.cat(14, 1.1)
    assert fidelity(st, st) == pytest.approx(1.0, abs=1e-12)


def test_fidelity_orthogonal() -> None:
    assert fidelity(FockState.fock(0, 8), FockState.fock(3, 8)) == pytest.approx(0.0, abs=1e-14)


def test_fidelity_pure_vs_density_is_expectation() -> None:
    """F(|ψ⟩, ρ) = ⟨ψ|ρ|ψ⟩ (Uhlmann reduces to expectation)."""
    psi = FockState.coherent(14, 0.7)
    d = FockDensity.thermal(14, 0.5)
    f = fidelity(psi, d)
    exp = np.real(np.vdot(psi.amps, d.rho @ psi.amps)) / np.real(np.trace(d.rho))
    assert f == pytest.approx(exp, abs=1e-7)


def test_fidelity_density_mixed_mixed() -> None:
    d1 = FockDensity.thermal(12, 0.4)
    d2 = FockDensity.thermal(12, 0.4)
    assert fidelity(d1, d2) == pytest.approx(1.0, abs=1e-8)
    d3 = FockDensity.thermal(12, 1.5)
    assert 0.0 < fidelity(d1, d3) < 1.0


def test_fidelity_nmode_mismatch() -> None:
    # density on one side → density path → nmode guard actually fires
    d1 = FockDensity.from_pure(FockState.fock(0, 6))
    with pytest.raises(ValueError):
        fidelity(d1, FockState.fock2(0, 0, 6))
