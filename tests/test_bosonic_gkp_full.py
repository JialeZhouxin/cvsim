"""GKP full-pair cross on 1D x-comb."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import gkp0, gkp1, weight_sum
from cvsim.wigner import wigner_grid


def test_full_count_and_weight_sum():
    N = 2
    st = gkp0(0.2, grid_size=N, cross="full")
    # K = (2N+1)^2 = 25
    assert st.n_components == (2 * N + 1) ** 2
    assert abs(weight_sum(st) - 1.0) < 1e-12


def test_full_contains_nn_midpoints():
    eps, N = 0.2, 2
    delta = np.sqrt(2.0 * np.pi)
    full = gkp0(eps, grid_size=N, cross="full")
    nn_mids = {0.5 * (k + k + 1) * delta for k in range(-N, N)}
    cross_xs = {
        float(c.rbar[0].real)
        for c in full.components
        if abs(c.rbar[1].imag) > 1e-14
    }
    for m in nn_mids:
        assert any(abs(x - m) < 1e-12 for x in cross_xs)


def test_full_wigner_differs_from_none():
    eps, N = 0.35, 2
    none = gkp0(eps, grid_size=N, cross="none")
    full = gkp0(eps, grid_size=N, cross="full")
    _, _, W0 = wigner_grid(none, lim=6.0, n=31)
    _, _, W1 = wigner_grid(full, lim=6.0, n=31)
    assert float(np.max(np.abs(W1 - W0))) > 1e-4


def test_gkp1_full_count_and_shift():
    eps, N = 0.15, 2
    z0 = gkp0(eps, grid_size=N, cross="full")
    z1 = gkp1(eps, grid_size=N, cross="full")
    assert z0.n_components == z1.n_components == (2 * N + 1) ** 2
    assert abs(weight_sum(z1) - 1.0) < 1e-12
    # diagonal peaks half-shift
    d0 = sorted(float(c.rbar[0].real) for c in z0.components if abs(c.rbar[1].imag) < 1e-14)
    d1 = sorted(float(c.rbar[0].real) for c in z1.components if abs(c.rbar[1].imag) < 1e-14)
    delta = np.sqrt(2.0 * np.pi)
    for a, b in zip(d0, d1):
        assert abs((b - a) - 0.5 * delta) < 1e-12


def test_full_bad_still_raises_typo():
    with pytest.raises(ValueError):
        gkp0(cross="fulll")  # type: ignore[arg-type]
