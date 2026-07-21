"""Fock two-mode squeeze S2."""

from __future__ import annotations

import numpy as np

from cvsim.fock import FockState, mean_photon, norm, two_mode_squeeze
from cvsim.gaussian import GaussianState
from cvsim.gaussian import mean_photon as g_n
from cvsim.gaussian import two_mode_squeeze as g_tms


def test_fock_s2_photon():
    r = 0.35
    N = 24
    st = two_mode_squeeze(FockState.vacuum(N, nmode=2), r)
    n_ex = float(np.sinh(r) ** 2)
    assert abs(mean_photon(st, 0) - n_ex) < 5e-3
    assert abs(mean_photon(st, 1) - n_ex) < 5e-3
    assert abs(mean_photon(st) - 2 * n_ex) < 1e-2
    assert norm(st) > 0.99


def test_fock_s2_near_gaussian():
    r = 0.3
    N = 28
    f = two_mode_squeeze(FockState.vacuum(N, nmode=2), r)
    g = g_tms(GaussianState.vacuum(2), r, 0, 1)
    assert abs(mean_photon(f) - g_n(g)) < 1e-2
