"""B1 Fock single-mode D/R/S."""

from __future__ import annotations

import numpy as np

from cvsim.fock import FockState, displace, mean_photon, phase, squeeze
from cvsim.gaussian import GaussianState, displace as g_disp, mean_photon as g_n


def test_displace_mean_photon_cutoff():
    alpha = 0.5
    st = displace(FockState.vacuum(30), alpha)
    assert abs(mean_photon(st) - abs(alpha) ** 2) < 1e-3


def test_fock_matches_gaussian_displace():
    alpha = 0.4 + 0.1j
    g = g_n(g_disp(GaussianState.vacuum(1), alpha))
    err_low = abs(mean_photon(displace(FockState.vacuum(8), alpha)) - g)
    err_hi = abs(mean_photon(displace(FockState.vacuum(25), alpha)) - g)
    assert err_hi < err_low
    assert err_hi < 1e-3


def test_phase_preserves_populations():
    st = squeeze(FockState.vacuum(20), 0.4)
    n0 = mean_photon(st)
    st2 = phase(st, 0.7)
    assert abs(mean_photon(st2) - n0) < 1e-12
    # overall global phase on each n differs
    assert not np.allclose(st2.amps, st.amps)
