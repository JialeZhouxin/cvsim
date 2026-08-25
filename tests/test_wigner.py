"""Single-mode Wigner G+B."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic import BosonicState, odd_cat
from cvsim.gaussian import GaussianState, squeeze
from cvsim.wigner import wigner_bosonic, wigner_gaussian, wigner_grid


def test_vacuum_center():
    st = GaussianState.vacuum(1)
    w0 = wigner_gaussian(st, 0.0, 0.0)
    assert abs(w0 - 1.0 / np.pi) < 1e-12
    # radial decay
    assert wigner_gaussian(st, 1.0, 0.0) < w0
    assert wigner_gaussian(st, 2.0, 0.0) < wigner_gaussian(st, 1.0, 0.0)


def test_squeeze_sharper_in_x():
    r = 0.6
    st = squeeze(GaussianState.vacuum(1), r)
    # peak at 0 still; compare W along x vs p at same |q|
    wx = wigner_gaussian(st, 0.4, 0.0)
    wp = wigner_gaussian(st, 0.0, 0.4)
    # squeezed in x → W falls slower along p (broader p), faster along x
    assert wx < wp


def test_odd_cat_has_negative():
    # even cat: constructive at origin; odd: destructive → W(0,0)<0
    st = odd_cat(1.2)
    assert wigner_bosonic(st, 0.0, 0.0) < -1e-3
    _, _, W = wigner_grid(st, lim=4.0, n=41)
    assert W.min() < -1e-3


def test_single_component_matches_gaussian():
    g = squeeze(GaussianState.vacuum(1), 0.4)
    b = BosonicState.from_gaussian(g)
    for x, p in [(0.0, 0.0), (0.5, -0.3), (1.0, 0.2)]:
        assert abs(wigner_bosonic(b, x, p) - wigner_gaussian(g, x, p)) < 1e-12
