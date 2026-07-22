"""GKP Gram explicit + 2d full + logical overlap (δ3)."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import gkp0, gkp1, gkp_logical_overlap, weight_sum
from cvsim.bosonic.gkp import _gauss_overlap


def test_gauss_overlap_1d_matches_legacy():
    eps = 0.25
    V = 0.5 * np.diag([eps, 1.0 / eps])
    delta = np.sqrt(2.0 * np.pi)
    r0 = np.array([0.0, 0.0])
    r1 = np.array([delta, 0.0])
    ov = _gauss_overlap(V, r0, r1)
    expect = float(np.exp(-np.pi / (2.0 * eps)))
    assert abs(ov - expect) < 1e-12


def test_1d_full_still_k_and_sum():
    N = 2
    st = gkp0(0.2, grid_size=N, cross="full")
    assert st.n_components == (2 * N + 1) ** 2
    assert abs(weight_sum(st) - 1.0) < 1e-12


def test_2d_full_count():
    N = 1
    M = (2 * N + 1) ** 2  # 9 peaks
    st = gkp0(0.2, grid_size=N, lattice="2d", cross="full")
    assert st.n_components == M * M  # 81
    assert abs(weight_sum(st) - 1.0) < 1e-12


def test_2d_nn_still_raises():
    with pytest.raises(ValueError, match="nn"):
        gkp0(lattice="2d", cross="nn")


def test_logical_overlap_self_full():
    st = gkp0(0.15, grid_size=2, cross="full")
    ov = gkp_logical_overlap(st, st)
    assert abs(ov - 1.0) < 1e-10


def test_logical_overlap_0_vs_1_small():
    eps, N = 0.08, 2
    z0 = gkp0(eps, grid_size=N, cross="full")
    z1 = gkp1(eps, grid_size=N, cross="full")
    ov = gkp_logical_overlap(z0, z1)
    assert abs(ov) < 0.5
