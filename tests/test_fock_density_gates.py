"""FockDensity gates: UρU† for D/R/S."""

from __future__ import annotations

import numpy as np

from cvsim.fock import FockDensity, FockState, loss, mean_photon, trace
from cvsim.fock.gates import displace, phase, squeeze


def test_density_displace_matches_pure():
    pure = FockState.vacuum(16)
    pure_d = displace(pure, 0.5 + 0.1j)
    dens = displace(FockDensity.from_pure(pure), 0.5 + 0.1j)
    dens_from_pure = FockDensity.from_pure(pure_d)
    assert np.allclose(dens.rho, dens_from_pure.rho, atol=1e-10)


def test_density_phase_squeeze_match_pure():
    pure = FockState.fock(1, 12)
    dens0 = FockDensity.from_pure(pure)
    for fn, args in [
        (phase, (0.7,)),
        (squeeze, (0.35,)),
    ]:
        p2 = fn(pure, *args)
        d2 = fn(dens0, *args)
        assert np.allclose(d2.rho, FockDensity.from_pure(p2).rho, atol=1e-10)


def test_loss_then_displace_trace():
    rho = loss(FockState.fock(1, 12), 0.4)
    rho2 = displace(rho, 0.3)
    assert abs(trace(rho2) - 1.0) < 1e-10
    assert mean_photon(rho2) > mean_photon(rho) - 1e-6
