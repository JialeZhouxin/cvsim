"""Fock 2-mode pure loss (Kraus kron)."""

from __future__ import annotations

import numpy as np

from cvsim.fock import (
    FockDensity,
    FockState,
    displace,
    loss,
    mean_photon,
    pnrd_probs,
    trace,
)


def test_T1_two_mode_identity():
    psi = FockState.fock2(1, 0, cutoff=6)
    rho = loss(psi, 1.0, mode=0)
    expect = FockDensity.from_pure(psi)
    assert rho.nmode == 2
    assert np.allclose(rho.rho, expect.rho, atol=1e-12)
    assert abs(trace(rho) - 1.0) < 1e-12


def test_fock10_mode0_like_1mode():
    T = 0.35
    N = 8
    psi2 = FockState.fock2(1, 0, cutoff=N)
    rho2 = loss(psi2, T, mode=0)
    # marginal mode0 ~ 1-mode |1⟩ loss
    p0 = pnrd_probs(rho2, mode=0)
    assert abs(p0[0] - (1.0 - T)) < 1e-12
    assert abs(p0[1] - T) < 1e-12
    assert mean_photon(rho2, 1) < 1e-12
    assert abs(mean_photon(rho2, 0) - T) < 1e-12
    assert abs(trace(rho2) - 1.0) < 1e-12


def test_fock01_mode0_untouched():
    T = 0.4
    N = 8
    psi2 = FockState.fock2(0, 1, cutoff=N)
    rho2 = loss(psi2, T, mode=0)
    # mode0 vacuum → still vacuum; mode1 still ~1
    assert mean_photon(rho2, 0) < 1e-12
    assert abs(mean_photon(rho2, 1) - 1.0) < 1e-12
    p1 = pnrd_probs(rho2, mode=1)
    assert abs(p1[1] - 1.0) < 1e-12


def test_both_modes_serial():
    N = 6
    psi = FockState.fock2(1, 1, cutoff=N)
    rho = loss(psi, 0.5)  # both
    assert rho.nmode == 2
    assert abs(trace(rho) - 1.0) < 1e-12
    # each mode lost some; total < 2
    assert mean_photon(rho) < 1.5


def test_coherent_tensor_vac_mode0():
    alpha = 0.7
    T = 0.5
    N = 16
    # |α⟩ ⊗ |0⟩
    a0 = displace(FockState.vacuum(N), alpha).amps
    amps = np.zeros((N, N), dtype=complex)
    amps[:, 0] = a0
    psi = FockState(amps=amps)
    rho = loss(psi, T, mode=0)
    assert abs(mean_photon(rho, 0) - T * abs(alpha) ** 2) < 0.05
    assert mean_photon(rho, 1) < 1e-10


def test_one_mode_still_works():
    psi = FockState.fock(1, cutoff=6)
    rho = loss(psi, 0.3)
    assert rho.nmode == 1
    assert abs(rho.rho[0, 0] - 0.7) < 1e-12
