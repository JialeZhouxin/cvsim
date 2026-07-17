"""B1 Gaussian: D, R, S, BS acceptance."""

from __future__ import annotations

import numpy as np

from cvsim.gaussian import (
    GaussianState,
    beamsplitter,
    det_cov,
    displace,
    mean_photon,
    phase,
    squeeze,
)
from cvsim.gaussian.symplectic import S_phase


def test_displace_mean_photon():
    alpha = 0.6 + 0.3j
    st = displace(GaussianState.vacuum(1), alpha)
    assert abs(mean_photon(st) - abs(alpha) ** 2) < 1e-12


def test_squeeze_bs_photon_conserved():
    r = 0.5
    st = squeeze(GaussianState.vacuum(2), r=r, mode=0)
    st = beamsplitter(st, 0, 1, theta=np.pi / 4, phi=0.0)
    n_tot = mean_photon(st)
    assert abs(n_tot - np.sinh(r) ** 2) < 1e-12
    # pure two-mode Gaussian: det V = (1/4)^2
    assert abs(det_cov(st) - (0.25) ** 2) < 1e-10


def test_phase_rotates_squeezed_cov():
    r, theta = 0.8, 0.4
    st = squeeze(GaussianState.vacuum(1), r=r)
    st2 = phase(st, theta)
    S = S_phase(1, theta, 0)
    expect = S @ st.V @ S.T
    assert np.allclose(st2.V, expect, atol=1e-12)
    assert abs(st2.V[0, 1]) > 1e-6  # off-diagonal after rotation


def test_bs_phi_symplectic_path():
    st = squeeze(GaussianState.vacuum(2), 0.3, 0)
    st = beamsplitter(st, 0, 1, 0.3, phi=0.5)
    assert abs(mean_photon(st) - np.sinh(0.3) ** 2) < 1e-12
