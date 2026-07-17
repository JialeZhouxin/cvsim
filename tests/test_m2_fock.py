"""M2: Fock squeeze cutoff scan + truncation deficit."""

from __future__ import annotations

import numpy as np

from cvsim.fock import FockState, mean_photon, norm, squeeze


def test_vacuum_norm():
    st = FockState.vacuum(8)
    assert abs(norm(st) - 1.0) < 1e-15
    assert abs(mean_photon(st)) < 1e-15


def test_squeeze_cutoff_approaches_analytic():
    r = 0.5
    exact = float(np.sinh(r) ** 2)
    err4 = abs(mean_photon(squeeze(FockState.vacuum(4), r)) - exact)
    err20 = abs(mean_photon(squeeze(FockState.vacuum(20), r)) - exact)
    assert err20 < err4
    assert err20 / max(exact, 1e-12) < 1e-3


def test_truncation_projection_deficit():
    r = 0.5
    rich = squeeze(FockState.vacuum(40), r)
    low = FockState(amps=rich.amps[:4].copy())
    deficit = 1.0 - norm(low)
    assert deficit > 1e-4
