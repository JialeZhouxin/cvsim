"""Single-mode Fock Wigner (ħ=1)."""

from __future__ import annotations

import numpy as np

from cvsim.fock import FockDensity, FockState, squeeze as f_squeeze
from cvsim.gaussian import GaussianState, squeeze as g_squeeze
from cvsim.wigner import wigner_fock, wigner_gaussian, wigner_grid


def test_fock_vacuum_center():
    st = FockState.vacuum(8)
    assert abs(wigner_fock(st, 0.0, 0.0) - 1.0 / np.pi) < 1e-12


def test_fock_one_negative_center():
    st = FockState.fock(1, 8)
    assert wigner_fock(st, 0.0, 0.0) < -1e-3
    assert abs(wigner_fock(st, 0.0, 0.0) + 1.0 / np.pi) < 1e-10


def test_fock_density_matches_pure():
    pure = FockState.fock(1, 6)
    dens = FockDensity.from_pure(pure)
    for x, p in [(0.0, 0.0), (0.5, -0.2)]:
        assert abs(wigner_fock(dens, x, p) - wigner_fock(pure, x, p)) < 1e-12


def test_fock_squeeze_near_gaussian():
    r = 0.3
    N = 24
    f = f_squeeze(FockState.vacuum(N), r)
    g = g_squeeze(GaussianState.vacuum(1), r)
    for x, p in [(0.0, 0.0), (0.3, 0.0), (0.0, 0.3)]:
        assert abs(wigner_fock(f, x, p) - wigner_gaussian(g, x, p)) < 5e-3


def test_fock_grid_vac():
    _, _, W = wigner_grid(FockState.vacuum(6), lim=2.0, n=11)
    mid = W.shape[0] // 2
    assert abs(W[mid, mid] - 1.0 / np.pi) < 1e-10
