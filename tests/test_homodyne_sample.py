"""Homodyne sampling: G exact edge + B real-peak mixture."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic import BosonicState, even_cat
from cvsim.bosonic import homodyne_sample as b_sample
from cvsim.gaussian import GaussianState, squeeze
from cvsim.gaussian import homodyne_sample as g_sample


def test_g_vacuum_stats():
    rng = np.random.default_rng(0)
    st = GaussianState.vacuum(1)
    xs = np.array([g_sample(st, rng=rng) for _ in range(5000)])
    assert abs(xs.mean()) < 0.05
    assert abs(xs.var(ddof=1) - 0.5) < 0.05


def test_g_squeeze_var():
    r = 0.6
    expect = 0.5 * np.exp(-2 * r)
    rng = np.random.default_rng(1)
    st = squeeze(GaussianState.vacuum(1), r)
    xs = np.array([g_sample(st, 0, 0.0, rng=rng) for _ in range(8000)])
    assert abs(xs.var(ddof=1) - expect) < 0.08


def test_b_from_gaussian_matches_g_repro():
    st_g = squeeze(GaussianState.vacuum(1), 0.4)
    st_b = BosonicState.from_gaussian(st_g)
    o_g = g_sample(st_g, rng=np.random.default_rng(42))
    o_b = b_sample(st_b, rng=np.random.default_rng(42))
    assert abs(o_g - o_b) < 1e-12


def test_even_cat_both_peaks():
    alpha = 1.0
    rx = np.sqrt(2.0) * alpha
    rng = np.random.default_rng(2)
    st = even_cat(alpha)
    xs = np.array([b_sample(st, rng=rng) for _ in range(400)])
    # neighbourhood of each peak
    n_plus = int(np.sum(np.abs(xs - rx) < 1.2))
    n_minus = int(np.sum(np.abs(xs + rx) < 1.2))
    assert n_plus >= 1 and n_minus >= 1


def test_same_seed_repro():
    st = GaussianState.vacuum(1)
    a = g_sample(st, rng=np.random.default_rng(99))
    b = g_sample(st, rng=np.random.default_rng(99))
    assert a == b
