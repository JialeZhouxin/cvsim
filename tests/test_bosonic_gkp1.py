"""GKP |1⟩ half-shift tooth-comb construction."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import gkp0, gkp1, phase, squeeze, weight_sum


def test_gkp1_count_and_weight_sum():
    st = gkp1(0.1, grid_size=3)
    assert st.n_components == 7  # same K as gkp0
    assert abs(weight_sum(st) - 1.0) < 1e-12


def test_gkp1_spacing():
    st = gkp1(0.1, grid_size=2)
    xs = sorted(float(c.rbar[0].real) for c in st.components)
    delta = np.sqrt(2.0 * np.pi)
    for a, b in zip(xs, xs[1:]):
        assert abs((b - a) - delta) < 1e-12


def test_gkp1_half_shift_vs_gkp0():
    eps, N = 0.12, 2
    z0 = gkp0(eps, grid_size=N)
    z1 = gkp1(eps, grid_size=N)
    delta = np.sqrt(2.0 * np.pi)
    xs0 = sorted(float(c.rbar[0].real) for c in z0.components)
    xs1 = sorted(float(c.rbar[0].real) for c in z1.components)
    assert len(xs0) == len(xs1)
    for a, b in zip(xs0, xs1):
        assert abs((b - a) - 0.5 * delta) < 1e-12


def test_gkp1_nn_count():
    st = gkp1(0.2, grid_size=2, cross="nn")
    assert st.n_components == 13
    assert abs(weight_sum(st) - 1.0) < 1e-12


def test_gkp1_gates_keep_weights():
    st = gkp1(0.15, grid_size=2)
    w0 = [c.w for c in st.components]
    st2 = squeeze(phase(st, 0.3), 0.2)
    assert all(abs(a - b) < 1e-15 for a, b in zip(w0, [c.w for c in st2.components]))


def test_gkp1_bad_args():
    with pytest.raises(ValueError):
        gkp1(epsilon=0.0)
    with pytest.raises(ValueError):
        gkp1(cross="pair")  # type: ignore[arg-type]
