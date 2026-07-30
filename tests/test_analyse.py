"""Tests for F-ANALYSE-1: symplectic_eigenvalues + purity."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import (
    GaussianState,
    is_physical,
    loss,
    purity,
    symplectic_eigenvalues,
)
from cvsim.gaussian.analyse import _as_cov


ATOL = 1e-10


# ---------------------------------------------------------------------------
# vacuum
# ---------------------------------------------------------------------------


def test_vacuum_purity_one():
    for m in (1, 2, 3):
        st = GaussianState.vacuum(m)
        assert purity(st) == pytest.approx(1.0, abs=ATOL)


def test_vacuum_symplectic_eigenvalues():
    for m in (1, 2, 3):
        st = GaussianState.vacuum(m)
        nu = symplectic_eigenvalues(st)
        assert nu.shape == (m,)
        assert np.allclose(nu, 0.5, atol=ATOL)


# ---------------------------------------------------------------------------
# thermal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("nbar", [0.0, 0.5, 1.0, 2.0])
def test_thermal_purity(nbar):
    st = GaussianState.thermal(nbar, nmode=1, mode=0)
    expected = 1.0 / (2.0 * nbar + 1.0)
    assert purity(st) == pytest.approx(expected, abs=ATOL)


@pytest.mark.parametrize("nbar", [0.0, 0.5, 1.0, 2.0])
def test_thermal_symplectic_eigenvalue(nbar):
    st = GaussianState.thermal(nbar, nmode=1, mode=0)
    nu = symplectic_eigenvalues(st)
    assert nu.shape == (1,)
    assert nu[0] == pytest.approx(nbar + 0.5, abs=ATOL)


# ---------------------------------------------------------------------------
# TMSV (pure two-mode)
# ---------------------------------------------------------------------------


def test_tmsv_pure_purity_and_eigs():
    st = GaussianState.tmsv(0.6, nmode=2, mode1=0, mode2=1)
    assert purity(st) == pytest.approx(1.0, abs=ATOL)
    nu = symplectic_eigenvalues(st)
    assert nu.shape == (2,)
    assert np.allclose(nu, 0.5, atol=ATOL)


# ---------------------------------------------------------------------------
# mixed: TMSV + loss
# ---------------------------------------------------------------------------


def test_tmsv_loss_mixed():
    st = GaussianState.tmsv(0.6, nmode=2, mode1=0, mode2=1)
    st = loss(st, 0.8, nbar=0.0)
    mu = purity(st)
    assert mu < 1.0 - ATOL
    assert mu > 0.0
    nu = symplectic_eigenvalues(st)
    assert nu.shape == (2,)
    assert np.all(nu >= 0.5 - ATOL)


# ---------------------------------------------------------------------------
# multi-mode thermal product (locks [::2] trap)
# ---------------------------------------------------------------------------


def test_thermal_product_unequal_nbar():
    """Unequal nbar → unequal ν; catches nu_all[m:] bug (must use [::2])."""
    t1 = GaussianState.thermal(0.3, nmode=1, mode=0)
    t2 = GaussianState.thermal(1.0, nmode=1, mode=0)
    prod = GaussianState.product(t1, t2)
    nu = symplectic_eigenvalues(prod)
    assert nu.shape == (2,)
    # ν = nbar + 1/2 → [0.8, 1.5]
    assert nu[0] == pytest.approx(0.8, abs=ATOL)
    assert nu[1] == pytest.approx(1.5, abs=ATOL)
    # purity = 1/(2ν1 · 2ν2) = 1/(1.6 · 3.0)
    expected_purity = 1.0 / (1.6 * 3.0)
    assert purity(prod) == pytest.approx(expected_purity, abs=ATOL)


# ---------------------------------------------------------------------------
# bare ndarray path
# ---------------------------------------------------------------------------


def test_bare_ndarray_vacuum():
    V = 0.5 * np.eye(2)
    assert purity(V) == pytest.approx(1.0, abs=ATOL)
    nu = symplectic_eigenvalues(V)
    assert nu.shape == (1,)
    assert nu[0] == pytest.approx(0.5, abs=ATOL)


def test_bare_ndarray_bad_shape_raises():
    with pytest.raises(ValueError, match="even square"):
        purity(np.eye(3))
    with pytest.raises(ValueError, match="even square"):
        symplectic_eigenvalues(np.ones((2, 3)))


# ---------------------------------------------------------------------------
# purity guard: non-PD V
# ---------------------------------------------------------------------------


def test_purity_non_pd_raises():
    # det < 0: diag(+1, -1) has det = -1
    V = np.diag([1.0, -1.0])
    with pytest.raises(ValueError, match="det\\(V\\)"):
        purity(V)
    # det == 0: singular
    V0 = np.zeros((2, 2))
    with pytest.raises(ValueError, match="det\\(V\\)"):
        purity(V0)


# ---------------------------------------------------------------------------
# cross-check: purity via ∏ 1/(2νⱼ)
# ---------------------------------------------------------------------------


def test_purity_cross_check_via_eigs():
    st = GaussianState.thermal(1.5, nmode=1, mode=0)
    nu = symplectic_eigenvalues(st)
    mu_from_eigs = float(np.prod(1.0 / (2.0 * nu)))
    assert purity(st) == pytest.approx(mu_from_eigs, abs=ATOL)

    st2 = GaussianState.product(
        GaussianState.thermal(0.2, nmode=1, mode=0),
        GaussianState.thermal(0.7, nmode=1, mode=0),
    )
    nu2 = symplectic_eigenvalues(st2)
    mu2_from_eigs = float(np.prod(1.0 / (2.0 * nu2)))
    assert purity(st2) == pytest.approx(mu2_from_eigs, abs=ATOL)


# ---------------------------------------------------------------------------
# is_physical still works after refactor to _as_cov
# ---------------------------------------------------------------------------


def test_is_physical_still_ok():
    assert is_physical(GaussianState.vacuum(1)) is True
    assert is_physical(GaussianState.thermal(1.0, nmode=1, mode=0)) is True
    assert is_physical(-np.eye(2)) is False


def test_as_cov_helper():
    st = GaussianState.vacuum(1)
    V = _as_cov(st)
    assert V.shape == (2, 2)
    assert np.allclose(V, 0.5 * np.eye(2))
