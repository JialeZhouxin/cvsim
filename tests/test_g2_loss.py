"""G2 photon loss channel."""

from __future__ import annotations

import numpy as np

from cvsim.gaussian import (
    GaussianState,
    displace,
    loss,
    mean_photon,
)


def test_t1_identity():
    st = displace(GaussianState.vacuum(1), 0.5 + 0.2j)
    st2 = loss(st, 1.0)
    assert np.allclose(st2.V, st.V)
    assert np.allclose(st2.rbar, st.rbar)


def test_t0_vacuum():
    st = displace(GaussianState.vacuum(2), 0.8, mode=0)
    st = displace(st, 0.3j, mode=1)
    st2 = loss(st, 0.0)
    assert np.allclose(st2.V, 0.5 * np.eye(4))
    assert np.allclose(st2.rbar, 0.0)


def test_coherent_photon_scales():
    alpha = 0.9 + 0.4j
    T = 0.35
    st = loss(displace(GaussianState.vacuum(1), alpha), T)
    assert abs(mean_photon(st) - T * abs(alpha) ** 2) < 1e-12


def test_single_mode_leaves_other():
    st = displace(GaussianState.vacuum(2), 0.7, mode=0)
    st = displace(st, 0.5, mode=1)
    st2 = loss(st, 0.2, mode=0)
    # mode 1 displacement untouched
    assert abs(st2.rbar[1] - st.rbar[1]) < 1e-12
    assert abs(st2.rbar[3] - st.rbar[3]) < 1e-12
    # mode 0 scaled
    assert abs(st2.rbar[0] - np.sqrt(0.2) * st.rbar[0]) < 1e-12
