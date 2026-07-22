"""GKP 2D diagonal lattice (δ2)."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import gkp0, gkp1, weight_sum


def test_2d_count_and_weight_sum():
    N = 1
    st = gkp0(0.15, grid_size=N, lattice="2d")
    assert st.n_components == (2 * N + 1) ** 2  # 9
    assert abs(weight_sum(st) - 1.0) < 1e-12


def test_2d_peaks_on_grid():
    eps, N = 0.2, 1
    delta = np.sqrt(2.0 * np.pi)
    st = gkp0(eps, grid_size=N, lattice="2d")
    pts = {(float(c.rbar[0].real), float(c.rbar[1].real)) for c in st.components}
    expect = {(k * delta, ell * delta) for k in range(-N, N + 1) for ell in range(-N, N + 1)}
    assert len(pts) == len(expect)
    for p in pts:
        assert any(abs(p[0] - e[0]) < 1e-12 and abs(p[1] - e[1]) < 1e-12 for e in expect)


def test_2d_V_isotropic():
    eps = 0.12
    st = gkp0(eps, grid_size=1, lattice="2d")
    V = st.components[0].V
    assert abs(V[0, 0] - 0.5 * eps) < 1e-14
    assert abs(V[1, 1] - 0.5 * eps) < 1e-14
    assert abs(V[0, 1]) < 1e-14


def test_gkp1_2d_half_shift_x():
    eps, N = 0.18, 1
    delta = np.sqrt(2.0 * np.pi)
    z0 = gkp0(eps, grid_size=N, lattice="2d")
    z1 = gkp1(eps, grid_size=N, lattice="2d")
    assert z0.n_components == z1.n_components
    # match by p (unchanged), x shifts by Δ/2
    by_p0 = {}
    for c in z0.components:
        p = float(c.rbar[1].real)
        by_p0.setdefault(round(p, 10), []).append(float(c.rbar[0].real))
    by_p1 = {}
    for c in z1.components:
        p = float(c.rbar[1].real)
        by_p1.setdefault(round(p, 10), []).append(float(c.rbar[0].real))
    for key in by_p0:
        xs0 = sorted(by_p0[key])
        xs1 = sorted(by_p1[key])
        for a, b in zip(xs0, xs1):
            assert abs((b - a) - 0.5 * delta) < 1e-12


def test_2d_cross_nn_raises():
    with pytest.raises(ValueError, match="2d"):
        gkp0(lattice="2d", cross="nn")


def test_1d_default_unchanged():
    st = gkp0(0.1, grid_size=2)
    assert st.n_components == 5  # 1d none
