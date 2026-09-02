"""GKP 2D: single-mode square-lattice, Z basis (alternating phase (−1)^k).

Per docs/gkp-2d-square-lattice.md §7 — single-mode position comb (peaks x=kΔ, p=0),
V = ½diag(ε,1/ε) (anisotropic, pure); gkp1 = alternating-phase comb (peaks same as
gkp0, phase (−1)^k), NOT half-period shift (that is the X basis, lattice="1d").
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import gkp0, gkp1, weight_sum


def test_2d_single_mode_count_and_weight_sum():
    N = 2
    st = gkp0(0.15, grid_size=N, lattice="2d")
    assert st.n_components == 2 * N + 1  # single-mode comb, not a 2D peak grid
    assert abs(weight_sum(st) - 1.0) < 1e-12

def test_2d_peaks_along_x_axis_only():
    eps, N = 0.2, 1
    delta = np.sqrt(2.0 * np.pi)
    st = gkp0(eps, grid_size=N, lattice="2d")
    pts = {(float(c.rbar[0].real), float(c.rbar[1].real)) for c in st.components}
    expect = {(k * delta, 0.0) for k in range(-N, N + 1)}
    assert len(pts) == len(expect)
    for p in pts:
        assert any(abs(p[0] - e[0]) < 1e-12 and abs(p[1] - e[1]) < 1e-12 for e in expect)

def test_2d_V_anisotropic_pure():
    eps = 0.12
    st = gkp0(eps, grid_size=1, lattice="2d")
    V = st.components[0].V
    assert abs(V[0, 0] - 0.5 * eps) < 1e-14      # squeezed x-width
    assert abs(V[1, 1] - 0.5 / eps) < 1e-14      # anti-squeezed p-width
    assert abs(V[0, 1]) < 1e-14

def test_2d_gkp0_same_comb_as_1d():
    # 2d gkp0 is the same single-mode position comb as 1d (peaks x=kΔ, V anisotropic).
    eps, N = 0.15, 2
    z1d = gkp0(eps, grid_size=N, lattice="1d")
    z2d = gkp0(eps, grid_size=N, lattice="2d")
    assert z1d.n_components == z2d.n_components == 2 * N + 1

def test_gkp1_2d_peaks_same_position_as_0():
    # Z basis: gkp1 peaks at the SAME (kΔ,0) positions as gkp0 (peak does NOT move).
    # The |0⟩ vs |1⟩ difference is the alternating phase, encoded in the cross
    # components' sign, not in peak positions. (Phase verified in test_gkp_2d_logical_z.)
    eps, N = 0.15, 1
    z0 = gkp0(eps, grid_size=N, lattice="2d")
    z1 = gkp1(eps, grid_size=N, lattice="2d")
    p0 = sorted((round(float(c.rbar[0].real), 12), round(float(c.rbar[1].real), 12))
                for c in z0.components)
    p1 = sorted((round(float(c.rbar[0].real), 12), round(float(c.rbar[1].real), 12))
                for c in z1.components)
    assert p0 == p1  # identical peak positions (only phase differs)

def test_2d_cross_nn_raises():
    with pytest.raises(ValueError, match="2d"):
        gkp0(lattice="2d", cross="nn")

def test_1d_default_unchanged():
    st = gkp0(0.1, grid_size=2)
    assert st.n_components == 5  # 1d none
