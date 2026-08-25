"""Bosonic photon loss (per-component, w fixed)."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic import (
    BosonicState,
    even_cat,
    homodyne_var,
    loss,
    mean_photon,
    weight_sum,
)
from cvsim.gaussian import (
    GaussianState,
)
from cvsim.gaussian import (
    displace as g_disp,
)
from cvsim.gaussian import (
    loss as g_loss,
)
from cvsim.gaussian import (
    mean_photon as g_n,
)


def test_t1_identity():
    st = even_cat(0.6)
    st2 = loss(st, 1.0)
    for a, b in zip(st.components, st2.components, strict=False):
        assert np.allclose(a.V, b.V)
        assert np.allclose(a.rbar, b.rbar)
        assert abs(a.w - b.w) < 1e-15


def test_single_component_matches_gaussian():
    alpha = 0.9 + 0.4j
    T = 0.35
    g = g_loss(g_disp(GaussianState.vacuum(1), alpha), T)
    b = loss(BosonicState.from_gaussian(g_disp(GaussianState.vacuum(1), alpha)), T)
    assert abs(mean_photon(b) - g_n(g)) < 1e-12
    assert abs(mean_photon(b) - T * abs(alpha) ** 2) < 1e-12


def test_cat_t0_vacuum_moments():
    st = loss(even_cat(0.8), 0.0)
    assert abs(weight_sum(st) - 1.0) < 1e-12
    assert abs(mean_photon(st)) < 1e-12
    assert abs(homodyne_var(st, 0, 0.0) - 0.5) < 1e-12


def test_weights_unchanged():
    st = even_cat(0.7)
    w0 = [c.w for c in st.components]
    st2 = loss(st, 0.4)
    assert all(abs(a - b) < 1e-15 for a, b in zip(w0, [c.w for c in st2.components], strict=False))
