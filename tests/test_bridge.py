"""F-BRIDGE tests — analytic matrix elements vs numerical Fock states.

Phase 5 exit 2: bridge tests for coherent/squeezed at low cutoff.
Analytic formulas in ``cvsim.bridge`` are compared against numerical
amplitudes from ``cvsim.fock`` (displace/squeeze applied to vacuum).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from cvsim import bridge
from cvsim.fock import FockState, displace, squeeze
from cvsim.gaussian import GaussianState
from cvsim.symplectic import S_squeeze, d_displace

# ---------------------------------------------------------------------------
# coherent_element vs Fock numerical
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("alpha", [0.0, 0.5, 1.0, 0.5 + 0.3j, -0.7 + 0.2j])
def test_coherent_element_matches_fock(alpha: complex) -> None:
    cutoff = 24  # expm displacement leaks amplitude near the truncation edge
    psi = displace(FockState.vacuum(cutoff), alpha)
    for n in range(10):
        got = bridge.coherent_element(n, alpha)
        np.testing.assert_allclose(got, psi.amps[n], atol=1e-9)


def test_coherent_element_known_values() -> None:
    # |α=0⟩ = |0⟩; ⟨0|0⟩=1, ⟨1|0⟩=0
    assert bridge.coherent_element(0, 0.0) == 1.0
    assert bridge.coherent_element(1, 0.0) == 0.0
    # ⟨0|1⟩ = e^{-1/2}
    np.testing.assert_allclose(bridge.coherent_element(0, 1.0), math.exp(-0.5))
    # ⟨1|1⟩ = e^{-1/2}
    np.testing.assert_allclose(bridge.coherent_element(1, 1.0), math.exp(-0.5))


def test_coherent_element_negative_n() -> None:
    with pytest.raises(ValueError):
        bridge.coherent_element(-1, 0.5)


# ---------------------------------------------------------------------------
# squeezed_element vs Fock numerical (real r, φ=0 convention)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("r", [0.2, 0.4, 0.7])
def test_squeezed_element_matches_fock(r: float) -> None:
    cutoff = 24  # expm squeeze leaks amplitude near the truncation edge
    psi = squeeze(FockState.vacuum(cutoff), r)
    for n in range(8):
        got = bridge.squeezed_element(n, r, phi=0.0)
        np.testing.assert_allclose(got, psi.amps[n], atol=1e-7)
    assert bridge.squeezed_element(1, r) == 0.0  # odd n vanish


def test_squeezed_element_known_values() -> None:
    r = 0.3
    # ⟨0|S(r)|0⟩ = 1/√cosh r ; ⟨2|S(r)|0⟩ = −tanh r / (√2 √cosh r)
    np.testing.assert_allclose(
        bridge.squeezed_element(0, r), 1 / math.sqrt(math.cosh(r)), atol=1e-12
    )
    np.testing.assert_allclose(
        bridge.squeezed_element(2, r),
        -math.tanh(r) / (math.sqrt(2.0) * math.sqrt(math.cosh(r))),
        atol=1e-12,
    )
    # vacuum (r=0): ⟨0|=1, others 0
    assert bridge.squeezed_element(0, 0.0) == 1.0
    assert bridge.squeezed_element(2, 0.0) == 0.0


def test_squeezed_element_negative_n() -> None:
    with pytest.raises(ValueError):
        bridge.squeezed_element(-1, 0.5)


# ---------------------------------------------------------------------------
# thermal_diag
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nbar", [0.0, 0.5, 2.0])
def test_thermal_diag_matches_manual(nbar: float) -> None:
    for n in range(5):
        got = bridge.thermal_diag(n, nbar)
        expected = nbar**n / (nbar + 1.0) ** (n + 1)
        np.testing.assert_allclose(got, expected, atol=1e-15)
    # vacuum n̄=0: only n=0 populated
    assert bridge.thermal_diag(0, 0.0) == 1.0
    assert bridge.thermal_diag(1, 0.0) == 0.0


def test_thermal_diag_negative() -> None:
    with pytest.raises(ValueError):
        bridge.thermal_diag(0, -1.0)


# ---------------------------------------------------------------------------
# vacuum_probability — analytic Gaussian vs Fock truncated ⟨0|ρ|0⟩
# ---------------------------------------------------------------------------


def _fock_p0(psi: FockState) -> float:
    """⟨0|ρ|0⟩ from a truncated pure state = |⟨0|ψ⟩|²."""
    return float(abs(psi.amps[0]) ** 2)


def test_vacuum_probability_vacuum() -> None:
    V = np.eye(2) * 0.5
    assert bridge.vacuum_probability(V, np.zeros(2), 0) == pytest.approx(1.0)


def test_vacuum_probability_coherent() -> None:
    # |α⟩: p₀ = e^{−|α|²} — both analytic and Fock
    for alpha in (0.3, 0.5 + 0.2j, 1.0):
        st_d = GaussianState(V=np.eye(2) * 0.5, rbar=_displace_vec(alpha))
        got = bridge.vacuum_probability(st_d.V, st_d.rbar, 0)
        np.testing.assert_allclose(got, math.exp(-(abs(alpha) ** 2)), atol=1e-12)
        # Fock cross-check at high cutoff
        psi = displace(FockState.vacuum(20), alpha)
        np.testing.assert_allclose(got, _fock_p0(psi), atol=1e-10)


def _displace_vec(alpha: complex) -> np.ndarray:
    """r̄ = √2 (Re α, Im α) in xxpp (ħ=1 conventions)."""
    return np.sqrt(2.0) * np.array([alpha.real, alpha.imag])


def test_vacuum_probability_squeezed() -> None:
    r = 0.5
    S = S_squeeze(1, r, 0)
    V = S @ (np.eye(2) * 0.5) @ S.T
    st = GaussianState(V=V, rbar=np.zeros(2))
    got = bridge.vacuum_probability(st.V, st.rbar, 0)
    # analytic: 1/√det(V+½I) with r̄=0
    expected = 1.0 / math.sqrt(np.linalg.det(V + 0.5 * np.eye(2)))
    np.testing.assert_allclose(got, expected, atol=1e-12)
    # Fock cross-check
    psi = squeeze(FockState.vacuum(16), r)
    np.testing.assert_allclose(got, _fock_p0(psi), atol=1e-10)


def test_vacuum_probability_squeezed_then_displaced() -> None:
    r, alpha = 0.4, 0.3 + 0.1j
    S = S_squeeze(1, r, 0)
    V = S @ (np.eye(2) * 0.5) @ S.T
    st = GaussianState(V=V, rbar=d_displace(1, alpha, 0))
    got = bridge.vacuum_probability(st.V, st.rbar, 0)
    # Fock cross-check: displace(squeeze(|0⟩))
    psi = displace(squeeze(FockState.vacuum(16), r), alpha)
    np.testing.assert_allclose(got, _fock_p0(psi), atol=1e-9)


def test_vacuum_probability_thermal_anchor() -> None:
    # thermal n̄: V = (n̄+½)I, r̄=0 → p₀ = 1/(n̄+1) = thermal_diag(0, n̄)
    for nbar in (0.5, 2.0):
        V = (nbar + 0.5) * np.eye(2)
        got = bridge.vacuum_probability(V, np.zeros(2), 0)
        np.testing.assert_allclose(got, 1.0 / (nbar + 1.0), atol=1e-12)
        np.testing.assert_allclose(got, bridge.thermal_diag(0, nbar), atol=1e-12)


def test_vacuum_probability_multimode_reduction() -> None:
    # 2-mode xxpp ordering: (x0, x1, p0, p1). Mode 0 hot (2I), mode 1
    # thermal-like (1.5I). Reduction must pick the right 2×2 corner.
    V = np.diag([2.0, 1.5, 2.0, 1.5])
    rbar = np.zeros(4)
    # mode 0: V00 = 2I → det(2.5I)=6.25 → p = 1/2.5 = 0.4
    got = bridge.vacuum_probability(V, rbar, 0)
    np.testing.assert_allclose(got, 1.0 / 2.5, atol=1e-12)
    # mode 1: V11 = 1.5I → det(2I)=4 → p = 1/2
    got1 = bridge.vacuum_probability(V, rbar, 1)
    np.testing.assert_allclose(got1, 1.0 / 2.0, atol=1e-12)
    # xxpp cross terms: off-diagonal x-p mixing must be picked up per mode
    Vx = np.diag([2.0, 1.5, 2.0, 1.5])
    Vx[0, 2] = Vx[2, 0] = 0.5  # mode-0 x–p correlation
    got_m0 = bridge.vacuum_probability(Vx, np.zeros(4), 0)
    # mode-0 block [[2,.5],[.5,2]] → A=[[2.5,.5],[.5,2.5]], det=6 → 1/√6
    np.testing.assert_allclose(got_m0, 1.0 / np.sqrt(6.0), atol=1e-12)
    got_m1 = bridge.vacuum_probability(Vx, np.zeros(4), 1)
    np.testing.assert_allclose(got_m1, 1.0 / 2.0, atol=1e-12)


def test_vacuum_probability_errors() -> None:
    V = np.eye(4) * 0.5
    with pytest.raises(IndexError):
        bridge.vacuum_probability(V, np.zeros(4), 5)
    with pytest.raises(ValueError):
        bridge.vacuum_probability(np.eye(3), np.zeros(3), 0)
    # non-PD V+½I
    with pytest.raises(ValueError):
        bridge.vacuum_probability(-np.eye(2), np.zeros(2), 0)
    # rbar shape mismatch
    with pytest.raises(ValueError):
        bridge.vacuum_probability(np.eye(4) * 0.5, np.zeros(3), 0)


# ---------------------------------------------------------------------------
# fock_state_amplitude helper
# ---------------------------------------------------------------------------


def test_fock_state_amplitude() -> None:
    psi = displace(FockState.vacuum(8), 0.4)
    assert bridge.fock_state_amplitude(0, psi) == psi.amps[0]
    assert bridge.fock_state_amplitude(3, psi) == psi.amps[3]
    with pytest.raises(IndexError):
        bridge.fock_state_amplitude(8, psi)  # outside cutoff


def test_fock_state_amplitude_multimode_rejected() -> None:
    psi2 = FockState.vacuum(8, nmode=2)
    with pytest.raises(ValueError):
        bridge.fock_state_amplitude(0, psi2)
