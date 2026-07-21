"""Thermal loss: Y=(1-T)(nbar+1/2)."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic import BosonicState
from cvsim.bosonic import loss as b_loss
from cvsim.bosonic import mean_photon as b_n
from cvsim.gaussian import GaussianState, displace, loss, mean_photon


def test_nbar0_matches_pure_loss():
    st = displace(GaussianState.vacuum(1), 0.6)
    a = loss(st, 0.4)
    b = loss(st, 0.4, nbar=0.0)
    assert np.allclose(a.V, b.V) and np.allclose(a.rbar, b.rbar)


def test_vacuum_full_thermal():
    nbar = 0.7
    st = loss(GaussianState.vacuum(1), 0.0, nbar=nbar)
    assert abs(mean_photon(st) - nbar) < 1e-12
    assert np.allclose(st.V, (nbar + 0.5) * np.eye(2))


def test_t1_identity_with_nbar():
    st = displace(GaussianState.vacuum(1), 0.3)
    st2 = loss(st, 1.0, nbar=2.0)
    assert np.allclose(st2.V, st.V) and np.allclose(st2.rbar, st.rbar)


def test_bosonic_matches_gaussian():
    nbar, T = 0.5, 0.3
    g = loss(GaussianState.vacuum(1), T, nbar=nbar)
    b = b_loss(BosonicState.from_gaussian(GaussianState.vacuum(1)), T, nbar=nbar)
    assert abs(b_n(b) - mean_photon(g)) < 1e-12
    assert np.allclose(b.components[0].V, g.V)
