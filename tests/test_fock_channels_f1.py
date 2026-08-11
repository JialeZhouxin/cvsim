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


def test_amplifier_2mode_preserves_other_mode() -> None:
    # |1⟩₀|2⟩₁ amplified on mode 0: mode-1 reduced state must stay |2⟩⟨2|
    c0 = np.zeros(6, complex)
    c0[1] = 1
    c1 = np.zeros(6, complex)
    c1[2] = 1
    st = FockState(amps=np.outer(c0, c1))
    d = amplifier(st, 1.5, mode=0)
    rho4 = d.rho.reshape(6, 6, 6, 6)
    red0 = np.einsum("abad->bd", rho4)  # trace mode0 → mode1 density
    tr = np.trace(red0).real
    assert 0.9 < tr < 1.0  # truncation-honest boundary (k loop early stop)
    red0_n = red0 / tr
    d1 = FockDensity.from_pure(FockState(amps=c1))
    np.testing.assert_allclose(red0_n, d1.rho, atol=1e-12)


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
    # coherence-detecting: A = diag(e^{iφn}) on mode 1 turns the |2,1⟩⟨2,0|
    # coherence (mode-1 photon numbers 1 vs 0) into ½e^{iφ}; wrong-mode
    # routing multiplies both by e^{2iφ} → coherence stays ½ (phase 0)
    phi = 0.7
    A = np.diag(np.exp(1j * phi * np.arange(6)))
    amps = np.zeros((6, 6), dtype=complex)
    amps[2, 1] = 1.0 / np.sqrt(2.0)
    amps[2, 0] = 1.0 / np.sqrt(2.0)
    st = FockState(amps=amps)
    d = apply_kraus(st, [A], mode=1)
    np.testing.assert_allclose(d.rho[2 * 6 + 1, 2 * 6 + 0], 0.5 * np.exp(1j * phi), atol=1e-12)


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
