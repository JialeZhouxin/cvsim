"""M1: Gaussian vacuum → squeeze → det V, ⟨n⟩."""

from __future__ import annotations

import numpy as np

from cvsim.gaussian import GaussianState, det_cov, mean_photon, squeeze


def test_vacuum_cov():
    st = GaussianState.vacuum(1)
    assert st.nmode == 1
    assert np.allclose(st.V, 0.5 * np.eye(2))
    assert np.allclose(st.rbar, 0.0)


def test_squeeze_analytic_v_and_n():
    r = 0.8
    st = squeeze(GaussianState.vacuum(1), r=r, mode=0)
    expect_v = 0.5 * np.diag([np.exp(-2 * r), np.exp(2 * r)])
    assert np.allclose(st.V, expect_v, atol=1e-12)
    assert abs(det_cov(st) - 0.25) < 1e-12
    assert abs(mean_photon(st) - np.sinh(r) ** 2) < 1e-12


def test_squeeze_mode_index_two_mode():
    r = 0.3
    st = squeeze(GaussianState.vacuum(2), r=r, mode=1)
    # mode 1 lives at x-index 1 and p-index 3 in xxpp
    assert abs(st.V[1, 1] - 0.5 * np.exp(-2 * r)) < 1e-12
    assert abs(st.V[3, 3] - 0.5 * np.exp(2 * r)) < 1e-12
    assert abs(st.V[0, 0] - 0.5) < 1e-12
    assert abs(mean_photon(st, mode=1) - np.sinh(r) ** 2) < 1e-12
    assert abs(mean_photon(st, mode=0)) < 1e-12
