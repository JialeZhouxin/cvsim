"""F1 channels: amplifier / phase_noise / apply_kraus (vision §4 F1,
Gaussian-matched conventions, ħ=1)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from cvsim.fock import FockDensity, FockState
from cvsim.fock.channels import amplifier, apply_kraus, phase_noise
from cvsim.fock.gates import squeeze
from cvsim.fock.observables import mean_photon

# -- amplifier -------------------------------------------------------------


def test_amplifier_vacuum_to_thermal() -> None:
    for G in (1.5, 2.0, 4.0):
        d = amplifier(FockState.vacuum(60), G)
        n = np.arange(60)
        p = np.diag(d.rho).real
        np.testing.assert_allclose(p, ((G - 1.0) / G) ** n / G, atol=1e-12)
        np.testing.assert_allclose(mean_photon(d), G - 1.0, atol=1e-3)


def test_amplifier_coherent_gain() -> None:
    st = FockState.coherent(20, 0.8)
    d = amplifier(st, 1.5)
    a = np.sqrt(np.arange(1, 20))
    amp_out = np.trace(d.rho @ np.diag(a, 1))
    np.testing.assert_allclose(abs(amp_out), 0.8 * np.sqrt(1.5), atol=1e-5)


def test_amplifier_against_gaussian() -> None:
    from cvsim.gaussian import GaussianState
    from cvsim.gaussian.channels import amplifier as g_amp

    r, G = 0.5, 1.7
    N = 30
    fst = squeeze(FockState.vacuum(N), r, 0)
    fd = amplifier(fst, G)
    gst = GaussianState.squeezed(r)
    gd = g_amp(gst, G)
    g_nbar = float(0.5 * (np.trace(gd.V) - 1.0))  # ⟨n⟩ = ½(tr V − 1), xxpp ħ=1
    np.testing.assert_allclose(mean_photon(fd), g_nbar, rtol=1e-4, atol=1e-4)


def test_amplifier_validation() -> None:
    with pytest.raises(ValueError):
        amplifier(FockState.vacuum(8), 0.5)
    with pytest.raises(NotImplementedError):
        amplifier(FockState.vacuum(8), 1.5, nbar=0.1)


# -- phase_noise -----------------------------------------------------------


def test_phase_noise_keeps_diagonal() -> None:
    st = FockState.coherent(15, 1.0)
    d = phase_noise(st, 0.5)
    np.testing.assert_allclose(np.diag(d.rho), abs(st.amps) ** 2, atol=1e-12)
    np.testing.assert_allclose(mean_photon(d), mean_photon(st), atol=1e-12)


def test_phase_noise_zero_is_identity_pure() -> None:
    st = FockState.fock2(1, 0, 8)
    d = phase_noise(st, 0.0, mode=0)
    np.testing.assert_allclose(d.rho, FockDensity.from_pure(st).rho, atol=1e-12)


def test_phase_noise_decoheres_coherence() -> None:
    st = FockState.coherent(10, 1.0)
    sigma = 2.0
    d = phase_noise(st, sigma)
    off = abs(d.rho[0, 1])
    c0c1 = abs(st.amps[0] * st.amps[1])
    np.testing.assert_allclose(off, c0c1 * np.exp(-sigma**2 / 2.0), atol=1e-12)


def test_phase_noise_closed_form() -> None:
    st = FockState.coherent(8, 0.7)
    sigma = 0.4
    d = phase_noise(st, sigma)
    n = np.arange(8)
    cm = np.exp(-sigma**2 / 2.0 * (n[:, None] - n[None, :]) ** 2)
    # ρ'_{nm} = c_n c_m* e^{−σ²(n−m)²/2}
    c = st.amps
    expected = np.outer(c, c.conj()) * cm
    np.testing.assert_allclose(d.rho, expected, atol=1e-12)


def test_phase_noise_thermal_rotation_closed_form() -> None:
    """ρ'_{nm} = ρ_{nm}·e^{−σ²(n−m)²/2}; for FockDensity input (thermal), diagonals
    survive exactly — the channel is a pure dephasing (⟨n⟩ invariant)."""
    d0 = FockDensity.thermal(12, 0.8)
    d1 = phase_noise(d0, 0.7)
    np.testing.assert_allclose(np.diag(d1.rho), np.diag(d0.rho), atol=1e-12)


# -- apply_kraus -----------------------------------------------------------


def test_apply_kraus_single_operator_preserves_pure() -> None:
    U = np.diag(np.exp(1j * np.arange(6)))
    st = FockState.fock(2, 6)
    d = apply_kraus(st, [U])
    np.testing.assert_allclose(d.rho[2, 2], 1.0, atol=1e-12)


def test_apply_kraus_matches_loss() -> None:
    from cvsim.fock.channels import loss

    T = 0.6
    st = FockState.coherent(10, 0.8)
    d_kraus = apply_kraus(st, _loss_kraus(10, T))
    d_loss = loss(st, T)
    np.testing.assert_allclose(d_kraus.rho, d_loss.rho, atol=1e-12)


def _loss_kraus(N: int, T: float) -> list[np.ndarray]:
    eta = 1.0 - T
    ks = []
    for k in range(N):
        A = np.zeros((N, N), dtype=complex)
        for n in range(k, N):
            A[n - k, n] = np.sqrt(math.comb(n, k) * T ** (n - k) * (1.0 - T) ** k)
        ks.append(A)
    return ks


def test_apply_kraus_mode_selection() -> None:
    st = FockState.fock2(1, 0, 6)
    # amplitude-damping single operator on mode 1 (identity-like for |0⟩)
    A = np.zeros((6, 6), dtype=complex)
    A[0, 0] = 1.0
    A[1, 1] = 1.0
    A[2, 2] = 1.0
    A[3, 3] = 1.0
    A[4, 4] = 1.0
    A[5, 5] = 1.0
    d = apply_kraus(st, [A], mode=1)
    np.testing.assert_allclose(d.rho[6, 6], 1.0, atol=1e-12)  # |1,0⟩ → idx 1·6+0


def test_apply_kraus_full_space() -> None:
    st = FockState.fock2(1, 0, 4)
    I = np.eye(4)
    U = np.kron(np.diag(np.exp(1j * np.arange(4))), I)
    d = apply_kraus(st, [U])
    np.testing.assert_allclose(d.rho[4, 4], 1.0, atol=1e-12)  # |1,0⟩ index = 1*4+0


def test_apply_kraus_validation() -> None:
    st = FockState.vacuum(4)
    with pytest.raises(ValueError):
        apply_kraus(st, [])
    with pytest.raises(ValueError):
        apply_kraus(st, [np.eye(3)])
    with pytest.raises(IndexError):
        apply_kraus(FockState.fock2(0, 0, 4), [np.eye(4)], mode=2)
