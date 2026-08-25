"""B3 two-mode squeeze S₂(r)."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic import two_mode_squeeze as b_tms
from cvsim.bosonic import weight_sum
from cvsim.bosonic.state import BosonicState, Component
from cvsim.conventions import omega, vacuum_cov
from cvsim.gaussian import (
    GaussianState,
    det_cov,
    mean_photon,
    two_mode_squeeze,
)
from cvsim.gaussian.symplectic import S_two_mode_squeeze


def test_s2_symplectic():
    for m, i, j in ((2, 0, 1), (3, 0, 2)):
        S = S_two_mode_squeeze(m, 0.55, i, j)
        Om = omega(m)
        assert np.allclose(S @ Om @ S.T, Om, atol=1e-12)


def test_s2_photon_and_det():
    r = 0.45
    st = two_mode_squeeze(GaussianState.vacuum(2), r, 0, 1)
    n0 = mean_photon(st, 0)
    n1 = mean_photon(st, 1)
    n_ex = np.sinh(r) ** 2
    assert abs(n0 - n_ex) < 1e-12
    assert abs(n1 - n_ex) < 1e-12
    assert abs(mean_photon(st) - 2 * n_ex) < 1e-12
    assert abs(det_cov(st) - 0.25**2) < 1e-10


def test_s2_correlation():
    r = 0.5
    st = two_mode_squeeze(GaussianState.vacuum(2), r, 0, 1)
    V = st.V
    # EPR: ⟨x0 x1⟩ and ⟨p0 p1⟩ nonzero (and opposite sign typically)
    assert abs(V[0, 1]) > 1e-6
    assert abs(V[2, 3]) > 1e-6
    assert V[0, 1] * V[2, 3] < 0


def test_bosonic_s2_matches_gaussian_and_weights():
    r = 0.4
    vac_g = two_mode_squeeze(GaussianState.vacuum(2), r, 0, 1)
    vac_b = BosonicState(
        components=[Component(V=vacuum_cov(2), rbar=np.zeros(4, dtype=complex), w=1.0)]
    )
    st_b = b_tms(vac_b, r, 0, 1)
    assert abs(weight_sum(st_b) - 1.0) < 1e-12
    assert np.allclose(st_b.components[0].V, vac_g.V, atol=1e-12)
