"""Bosonic moment loop: vacuum + weighted ⟨n⟩ / Homodyne."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic import (
    BosonicState,
    displace,
    even_cat,
    homodyne_mean,
    homodyne_var,
    mean_photon,
    phase,
    squeeze,
    weight_sum,
)
from cvsim.gaussian import (
    GaussianState,
)
from cvsim.gaussian import (
    displace as g_disp,
)
from cvsim.gaussian import (
    homodyne_mean as g_mean,
)
from cvsim.gaussian import (
    homodyne_var as g_var,
)
from cvsim.gaussian import (
    mean_photon as g_n,
)
from cvsim.gaussian import (
    squeeze as g_sq,
)


def test_vacuum_moments():
    st = BosonicState.vacuum(1)
    assert abs(weight_sum(st) - 1.0) < 1e-15
    assert abs(mean_photon(st)) < 1e-15
    for phi in (0.0, 0.3, np.pi / 2):
        assert abs(homodyne_mean(st, 0, phi)) < 1e-15
        assert abs(homodyne_var(st, 0, phi) - 0.5) < 1e-12


def test_single_component_matches_gaussian():
    alpha = 0.45 + 0.12j
    r = 0.35
    g = g_sq(g_disp(GaussianState.vacuum(1), alpha), r)
    b = BosonicState.from_gaussian(g)
    assert abs(mean_photon(b) - g_n(g)) < 1e-12
    for phi in (0.0, 0.4, np.pi / 2):
        assert abs(homodyne_mean(b, 0, phi) - g_mean(g, 0, phi)) < 1e-12
        assert abs(homodyne_var(b, 0, phi) - g_var(g, 0, phi)) < 1e-12


def test_even_cat_mean_photon_grows():
    n_lo = mean_photon(even_cat(0.5))
    n_hi = mean_photon(even_cat(1.0))
    assert abs(weight_sum(even_cat(0.5)) - 1.0) < 1e-12
    assert even_cat(0.5).n_components == 4
    assert n_lo > 0
    assert n_hi > n_lo


def test_cat_phase_preserves_weight_sum():
    st = even_cat(0.7)
    st2 = phase(st, 0.55)
    assert abs(weight_sum(st2) - weight_sum(st)) < 1e-14
    # single coherent peak: phase rotates mean; for cat mean stays ~0 at φ=0
    assert abs(homodyne_mean(st, 0, 0.0)) < 1e-10
    assert abs(homodyne_mean(st2, 0, 0.0)) < 1e-10


def test_gate_keeps_weights():
    st = even_cat(0.6)
    w0 = [c.w for c in st.components]
    st2 = squeeze(st, 0.2)
    st3 = displace(st2, 0.1)
    assert all(abs(a - b) < 1e-15 for a, b in zip(w0, [c.w for c in st3.components], strict=False))
