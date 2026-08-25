"""GKP |0⟩ diagonal tooth-comb construction."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic import gkp0, mean_photon, phase, squeeze, weight_sum


def test_gkp0_count_and_weight_sum():
    st = gkp0(0.1, grid_size=3)
    assert st.n_components == 7
    assert abs(weight_sum(st) - 1.0) < 1e-12


def test_gkp0_spacing():
    st = gkp0(0.1, grid_size=2)
    xs = sorted(float(c.rbar[0].real) for c in st.components)
    delta = np.sqrt(2.0 * np.pi)
    for a, b in zip(xs, xs[1:], strict=False):
        assert abs((b - a) - delta) < 1e-12


def test_gkp0_epsilon_mean_photon():
    n_fat = mean_photon(gkp0(0.5, grid_size=4))
    n_sharp = mean_photon(gkp0(0.05, grid_size=4))
    assert n_fat < n_sharp


def test_gkp0_gates_keep_weights():
    st = gkp0(0.15, grid_size=2)
    w0 = [c.w for c in st.components]
    st2 = squeeze(phase(st, 0.3), 0.2)
    assert all(abs(a - b) < 1e-15 for a, b in zip(w0, [c.w for c in st2.components], strict=False))


def test_gkp0_bad_args():
    import pytest

    with pytest.raises(ValueError):
        gkp0(epsilon=0.0)
    with pytest.raises(ValueError):
        gkp0(grid_size=-1)
