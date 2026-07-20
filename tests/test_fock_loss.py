"""Fock pure-loss channel (1-mode density Kraus)."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.fock import (
    FockDensity,
    FockState,
    displace,
    loss,
    mean_photon,
    pnrd_probs,
    trace,
)


def test_T1_identity():
    psi = FockState.fock(2, cutoff=6)
    rho = loss(psi, 1.0)
    expect = FockDensity.from_pure(psi).rho
    assert np.allclose(rho.rho, expect, atol=1e-12)
    assert abs(trace(rho) - 1.0) < 1e-12


def test_T0_vacuum():
    psi = FockState.fock(3, cutoff=8)
    rho = loss(psi, 0.0)
    assert abs(rho.rho[0, 0] - 1.0) < 1e-12
    assert abs(trace(rho) - 1.0) < 1e-12
    assert mean_photon(rho) < 1e-12


def test_fock1_diagonal():
    T = 0.3
    psi = FockState.fock(1, cutoff=6)
    rho = loss(psi, T)
    assert abs(rho.rho[0, 0] - (1.0 - T)) < 1e-12
    assert abs(rho.rho[1, 1] - T) < 1e-12
    assert abs(rho.rho[0, 1]) < 1e-12
    p = pnrd_probs(rho)
    assert abs(p[0] - (1.0 - T)) < 1e-12
    assert abs(p[1] - T) < 1e-12


def test_coherent_mean_photon():
    alpha = 0.8
    T = 0.55
    N = 24
    psi = displace(FockState.vacuum(N), alpha)
    rho = loss(psi, T)
    expect = T * abs(alpha) ** 2
    assert abs(mean_photon(rho) - expect) < 0.05


def test_two_mode_raises():
    psi = FockState.vacuum(4, nmode=2)
    with pytest.raises(ValueError):
        loss(psi, 0.5)


def test_bad_T_raises():
    psi = FockState.vacuum(4)
    with pytest.raises(ValueError):
        loss(psi, 1.5)
