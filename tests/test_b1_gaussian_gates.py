"""B1 Gaussian: D, R, S, BS, CZ, CX acceptance."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import (
    GaussianState,
    beamsplitter,
    cx,
    cz,
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


def test_cz_creates_photons():
    """CZ on vacuum: unitary, det V unchanged, but <n> > 0."""
    st = cz(GaussianState.vacuum(2), weight=0.5, mode1=0, mode2=1)
    assert abs(det_cov(st) - 0.25**2) < 1e-10  # pure
    assert mean_photon(st) > 0  # photons created
    # p₁ += g·x₂  manifests in V[2,1] = g/2
    assert abs(st.V[2, 1] - 0.5 / 2) < 1e-12


def test_cx_inverse():
    """CX(-g) after CX(g) returns to vacuum."""
    st = cx(GaussianState.vacuum(2), weight=0.3, mode1=0, mode2=1)
    st = cx(st, weight=-0.3, mode1=0, mode2=1)
    assert abs(det_cov(st) - 0.25**2) < 1e-10
    assert np.allclose(st.V, np.eye(4) / 2, atol=1e-12)
    assert np.allclose(st.rbar, 0, atol=1e-12)


def test_cz_cx_validation():
    """cz/cx raise ValueError on same mode."""
    vac = GaussianState.vacuum(2)
    with pytest.raises(ValueError, match="must differ"):
        cz(vac, 0.5, 0, 0)
    with pytest.raises(ValueError, match="must differ"):
        cx(vac, 0.5, 1, 1)


def test_cz_cx_export():
    """cz and cx importable from cvsim.gaussian."""
    from cvsim.gaussian import cx as cx2
    from cvsim.gaussian import cz as cz2
    assert callable(cz2)
    assert callable(cx2)
