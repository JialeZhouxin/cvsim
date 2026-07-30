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


# ---------------------------------------------------------------------------
# Review R1–R3 regressions (docs/review-07-30-phase2-analyse-eigs-purity.md)
# ---------------------------------------------------------------------------


def test_r1_purity_symmetrizes_asymmetric_v():
    """R1: purity must symmetrize so μ matches ∏ 1/(2ν) on asymmetric V."""
    V_therm = 1.5 * np.eye(2)
    V_asym = V_therm.copy()
    V_asym[0, 1] += 0.4
    V_asym[1, 0] -= 0.4
    nu = symplectic_eigenvalues(V_asym)
    mu = purity(V_asym)
    mu_cross = float(np.prod(1.0 / (2.0 * nu)))
    assert mu == pytest.approx(mu_cross, abs=ATOL)
    assert mu == pytest.approx(1.0 / 3.0, abs=ATOL)  # thermal nbar=0.5


def test_r2_nonphysical_silent_by_default_validate_raises():
    """R2: default allows non-physical; validate=True rejects."""
    V_sub = 0.4 * np.eye(2)
    assert is_physical(V_sub) is False
    # default: no raise, but μ > 1 is possible
    assert purity(V_sub) == pytest.approx(1.25, abs=ATOL)
    nu = symplectic_eigenvalues(V_sub)
    assert nu.shape == (1,)
    # validate=True must raise
    with pytest.raises(ValueError, match="non-physical"):
        purity(V_sub, validate=True)
    with pytest.raises(ValueError, match="non-physical"):
        symplectic_eigenvalues(V_sub, validate=True)


def test_r3_atol_affects_clip_floor():
    """R3: atol must change the vacuum-floor clip (no longer a dead param)."""
    # Construct V whose raw symplectic eig is slightly below 0.5
    # V = (0.5 - 1e-8) * I → ν_raw ≈ 0.5 - 1e-8
    eps = 1e-8
    V = (0.5 - eps) * np.eye(2)
    # default atol=1e-10: floor = 0.5 - 1e-10 ≈ 0.5, so clip up to ~0.5
    nu_default = symplectic_eigenvalues(V, atol=1e-10)
    assert nu_default[0] == pytest.approx(0.5 - 1e-10, abs=1e-15)
    # large atol=1e-6: floor = 0.5 - 1e-6; raw ν ≈ 0.5-1e-8 > floor → no clip to 0.5
    nu_loose = symplectic_eigenvalues(V, atol=1e-6)
    # raw should pass through near 0.5 - eps (above 0.5 - 1e-6)
    assert nu_loose[0] == pytest.approx(0.5 - eps, abs=1e-12)
    # different atol → different result (param is live)
    assert nu_default[0] != pytest.approx(nu_loose[0], abs=1e-15)
