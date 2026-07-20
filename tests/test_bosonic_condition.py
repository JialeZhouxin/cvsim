"""Bosonic ideal Homodyne condition (real peaks + drop cross)."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import (
    BosonicState,
    even_cat,
    homodyne_condition as b_cond,
    weight_sum,
)
from cvsim.gaussian import GaussianState, squeeze
from cvsim.gaussian import homodyne_condition as g_cond


def test_single_component_matches_gaussian():
    g0 = squeeze(GaussianState.vacuum(1), 0.5)
    b0 = BosonicState.from_gaussian(g0)
    out = 0.2
    g1 = g_cond(g0, 0, 0.0, out)
    b1 = b_cond(b0, 0, 0.0, out)
    assert b1.n_components == 1
    assert np.allclose(b1.components[0].V, g1.V)
    assert np.allclose(b1.components[0].rbar.real, g1.rbar)
    assert abs(weight_sum(b1) - 1.0) < 1e-12


def test_vacuum_outcome():
    g0 = GaussianState.vacuum(1)
    b0 = BosonicState.vacuum(1)
    out = 0.3
    g1 = g_cond(g0, 0, 0.0, out)
    b1 = b_cond(b0, 0, 0.0, out)
    assert np.allclose(b1.components[0].V, g1.V)
    assert np.allclose(b1.components[0].rbar.real, g1.rbar)
    assert abs(b1.components[0].rbar[0].real - out) < 1e-12


def test_even_cat_peak_selection():
    alpha = 0.8
    st = even_cat(alpha)
    outcome = np.sqrt(2.0) * alpha
    st2 = b_cond(st, 0, 0.0, outcome)
    assert abs(weight_sum(st2) - 1.0) < 1e-12
    for c in st2.components:
        assert np.max(np.abs(c.rbar.imag)) < 1e-12
    assert st2.n_components == 2  # two diagonal peaks; cross dropped
    # even_cat order: +diag, -diag first; condition keeps that order
    # ideal cond collapses x→outcome, so compare weights not post-mean
    w_plus = abs(st2.components[0].w)
    w_minus = abs(st2.components[1].w)
    assert w_plus > w_minus


def test_all_complex_raises():
    # two pure cross-like components
    from cvsim.bosonic.state import Component
    from cvsim.conventions import vacuum_cov

    V = vacuum_cov(1)
    st = BosonicState(
        components=[
            Component(V=V.copy(), rbar=np.array([0.0, 1j], dtype=complex), w=0.5),
            Component(V=V.copy(), rbar=np.array([0.0, -1j], dtype=complex), w=0.5),
        ]
    )
    with pytest.raises(ValueError):
        b_cond(st, 0, 0.0, 0.0)
