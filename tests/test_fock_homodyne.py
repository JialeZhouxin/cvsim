"""Fock 1-mode Homodyne mean/var/sample."""

from __future__ import annotations

import numpy as np
import pytest

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


# -- coverage supplement (2026-09-07): guards + density mixture path --------


def test_homodyne_mean_mode1_raises():
    """single-mode states only; mode=1 → IndexError."""
    st = FockState.vacuum(10)
    with pytest.raises(IndexError, match="mode must be 0"):
        homodyne_mean(st, mode=1)


def test_homodyne_mean_dens2_raises():
    """2-mode density → ValueError (single-mode only)."""
    import numpy as _np

    rho = _np.zeros((4, 4), dtype=complex)
    rho[0, 0] = 1.0
    d = FockDensity(rho=rho, nmode=2)
    with pytest.raises(ValueError, match="single-mode only"):
        homodyne_mean(d, mode=0)


def test_homodyne_sample_default_rng():
    """rng=None path (internal default_rng)."""
    out = homodyne_sample(FockState.coherent(12, 1.0))
    assert isinstance(out, float)


def test_homodyne_sample_n_grid_too_small():
    with pytest.raises(ValueError, match="n_grid"):
        homodyne_sample(FockState.vacuum(12), n_grid=2)


def test_homodyne_sample_zero_state():
    with pytest.raises(ValueError, match="zero state"):
        homodyne_sample(FockState(amps=np.zeros(12)))


def test_homodyne_sample_density_mixture_path():
    """density spectral mixture: coherent density samples finite value."""
    d = FockDensity.from_pure(FockState.coherent(16, 0.9))
    out = homodyne_sample(d, rng=np.random.default_rng(0))
    assert isinstance(out, float)
    assert abs(out) < 6.0  # lim=8 grid, coherent α=0.9


def test_pdf_from_amps_zero_pdf_raises():
    """_pdf_from_amps defensive branch: zero PDF sum → ValueError."""
    from cvsim.fock.observables import _pdf_from_amps

    qs = np.linspace(-8.0, 8.0, 513)
    with pytest.raises(ValueError, match="PDF sum"):
        _pdf_from_amps(np.zeros(4), qs)


def test_density_tiny_eigenvalue_skipped():
    """Density with a < 1e-14 eigenvalue: skipped in mixture loop (229)."""
    d = FockDensity.from_pure(FockState.coherent(8, 0.3))
    # inject a tiny eigenvalue into the density matrix
    rho = d.rho.copy()
    rho[1, 1] += 1e-15 * rho[0, 0]  # tiny weight on another basis vector
    d2 = FockDensity(rho=rho)
    out = homodyne_sample(d2, rng=np.random.default_rng(0))
    assert isinstance(out, float)


# ponytail: 238/242 为数值深防御（归一化后 w 总和=1 → 必有 wi≥1e-14 参与求和；
# 除非某本征向量零范数——ρ 有质量时不可能），正常逻辑不可达。已记录 design.md。
