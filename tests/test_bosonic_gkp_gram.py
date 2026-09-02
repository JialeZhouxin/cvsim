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
    # single-mode square lattice: M=2N+1 peaks; full cross -> M² components
    N = 1
    M = 2 * N + 1  # 3 peaks (not a 2D peak grid)
    st = gkp0(0.2, grid_size=N, lattice="2d", cross="full")
    assert st.n_components == M * M  # 9
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


def test_1d_cross_centre_phase_pinned():
    """Regression lock for the 1d cross-component Wigner phase (B7).

    For anisotropic V=½diag(ε,1/ε) the cross centre of |g_i⟩⟨g_j| is
    m = (r_i+r_j)/2 + i·s with s = V·J·(r_i−r_j). For adjacent comb teeth
    (Δx = Δ) this gives imag(p) = ±Δ/(2ε) — NOT the isotropic ±Δ/2. The
    value is the exact Wigner phase for anisotropic V (verified: it makes
    the cross state pure); this test pins it so future edits of
    _append_cross_pair_vec can't silently drift the 1d numerics.
    """
    eps, N = 0.2, 1
    delta = np.sqrt(2.0 * np.pi)
    st = gkp0(eps, grid_size=N, cross="nn")
    expect_half = delta / (2.0 * eps)
    expect_imag = delta / (2.0 * eps)  # Δx = Δ for adjacent teeth
    cross = [c for c in st.components if abs(c.rbar[1].imag) > 1e-14]
    assert len(cross) == 2 * (2 * N)  # 2 per adjacent pair, N=1
    for c in cross:
        # midpoint x of adjacent pair
        assert any(abs(abs(float(c.rbar[0].real)) - (k + 0.5) * delta) < 1e-12
                   for k in range(-N, N))
        assert abs(abs(float(c.rbar[1].imag)) - expect_imag) < 1e-10
