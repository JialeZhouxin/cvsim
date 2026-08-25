"""B2 Homodyne: Gaussian edge mean/var."""

from __future__ import annotations

import numpy as np

from cvsim.gaussian import (
    GaussianState,
    displace,
    homodyne_mean,
    homodyne_var,
    phase,
    squeeze,
)


def test_vacuum_mean_var_any_phi():
    st = GaussianState.vacuum(1)
    for phi in (0.0, 0.3, np.pi / 4, np.pi / 2, 1.7):
        assert abs(homodyne_mean(st, 0, phi)) < 1e-15
        assert abs(homodyne_var(st, 0, phi) - 0.5) < 1e-15


def test_squeeze_x_p_vars():
    r = 0.6
    st = squeeze(GaussianState.vacuum(1), r)
    assert abs(homodyne_var(st, 0, 0.0) - 0.5 * np.exp(-2 * r)) < 1e-12
    assert abs(homodyne_var(st, 0, np.pi / 2) - 0.5 * np.exp(2 * r)) < 1e-12


def test_displace_mean():
    alpha = 0.4 + 0.25j
    st = displace(GaussianState.vacuum(1), alpha)
    for phi in (0.0, 0.5, np.pi / 2):
        expect = np.sqrt(2) * (alpha.real * np.cos(phi) + alpha.imag * np.sin(phi))
        assert abs(homodyne_mean(st, 0, phi) - expect) < 1e-12
        # variance still vacuum
        assert abs(homodyne_var(st, 0, phi) - 0.5) < 1e-12


def test_phase_after_squeeze_matches_uVu():
    r, theta = 0.7, 0.35
    st = phase(squeeze(GaussianState.vacuum(1), r), theta)
    phi = 0.0
    c, s = np.cos(phi), np.sin(phi)
    V = st.V
    expect = c * c * V[0, 0] + s * s * V[1, 1] + 2 * s * c * V[0, 1]
    assert abs(homodyne_var(st, 0, phi) - expect) < 1e-12
    # rotated squeeze: x-var no longer pure e^{-2r}/2
    assert abs(homodyne_var(st, 0, 0.0) - 0.5 * np.exp(-2 * r)) > 1e-6
