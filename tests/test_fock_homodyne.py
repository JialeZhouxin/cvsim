"""Fock 1-mode Homodyne mean/var/sample."""

from __future__ import annotations

import numpy as np

from cvsim.fock import (
    FockDensity,
    FockState,
    displace,
    homodyne_mean,
    homodyne_sample,
    homodyne_var,
    squeeze,
)
from cvsim.gaussian import GaussianState
from cvsim.gaussian import displace as g_disp
from cvsim.gaussian import homodyne_mean as g_mean
from cvsim.gaussian import homodyne_var as g_var


def test_vac_mean_var():
    st = FockState.vacuum(12)
    assert abs(homodyne_mean(st)) < 1e-12
    assert abs(homodyne_var(st) - 0.5) < 1e-12
    assert abs(homodyne_var(st, phi=np.pi / 2) - 0.5) < 1e-12


def test_coherent_matches_gaussian():
    alpha = 0.55 + 0.2j
    N = 28
    f = displace(FockState.vacuum(N), alpha)
    g = g_disp(GaussianState.vacuum(1), alpha)
    for phi in (0.0, 0.4, np.pi / 2):
        assert abs(homodyne_mean(f, phi=phi) - g_mean(g, 0, phi)) < 1e-6
        assert abs(homodyne_var(f, phi=phi) - g_var(g, 0, phi)) < 5e-3


def test_squeeze_var():
    r = 0.4
    N = 28
    f = squeeze(FockState.vacuum(N), r)
    assert abs(homodyne_var(f, phi=0.0) - 0.5 * np.exp(-2 * r)) < 2e-2
    assert abs(homodyne_var(f, phi=np.pi / 2) - 0.5 * np.exp(2 * r)) < 2e-2


def test_density_matches_pure():
    pure = displace(FockState.vacuum(16), 0.4)
    dens = FockDensity.from_pure(pure)
    assert abs(homodyne_mean(dens) - homodyne_mean(pure)) < 1e-12
    assert abs(homodyne_var(dens) - homodyne_var(pure)) < 1e-12


def test_sample_vac_stats():
    rng = np.random.default_rng(0)
    st = FockState.vacuum(10)
    xs = np.array([homodyne_sample(st, rng=rng) for _ in range(3000)])
    assert abs(xs.mean()) < 0.08
    assert abs(xs.var(ddof=1) - 0.5) < 0.1
