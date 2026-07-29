"""F-STATE-FACTORY: coherent, thermal, squeezed, tmsv, product."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import (
    GaussianState,
    det_cov,
    homodyne_mean,
    homodyne_var,
    is_physical,
    mean_photon,
    two_mode_squeeze,
    validate_state,
)


def test_vacuum_factory():
    st = GaussianState.vacuum(3)
    assert st.nmode == 3
    np.testing.assert_allclose(st.V, 0.5 * np.eye(6))
    np.testing.assert_allclose(st.rbar, 0.0)
    assert st.is_physical()


def test_coherent_mean_and_purity():
    alpha = 0.5 - 0.25j
    st = GaussianState.coherent(alpha)
    np.testing.assert_allclose(st.rbar[0], np.sqrt(2) * alpha.real)
    np.testing.assert_allclose(st.rbar[1], np.sqrt(2) * alpha.imag)
    np.testing.assert_allclose(st.V, 0.5 * np.eye(2))
    np.testing.assert_allclose(det_cov(st), 0.25)
    np.testing.assert_allclose(homodyne_mean(st, 0, 0.0), st.rbar[0])


def test_thermal_covariance_and_nbar():
    nbar = 1.5
    st = GaussianState.thermal(nbar)
    scale = 0.5 * (2 * nbar + 1)
    np.testing.assert_allclose(st.V, scale * np.eye(2))
    # <n> = nbar for thermal centered
    np.testing.assert_allclose(mean_photon(st), nbar, atol=1e-12)
    with pytest.raises(ValueError):
        GaussianState.thermal(-0.1)


def test_squeezed_variances_phi0():
    r = 0.6
    st = GaussianState.squeezed(r)
    np.testing.assert_allclose(homodyne_var(st, 0, 0.0), 0.5 * np.exp(-2 * r))
    np.testing.assert_allclose(homodyne_var(st, 0, np.pi / 2), 0.5 * np.exp(2 * r))
    np.testing.assert_allclose(det_cov(st), 0.25, atol=1e-12)


def test_squeezed_with_phi_rotates():
    r, phi = 0.5, np.pi / 4
    st = GaussianState.squeezed(r, phi=phi)
    # still pure
    np.testing.assert_allclose(det_cov(st), 0.25, atol=1e-12)
    # var along phi should be squeezed axis ≈ e^{-2r}/2
    v_phi = homodyne_var(st, 0, phi)
    np.testing.assert_allclose(v_phi, 0.5 * np.exp(-2 * r), atol=1e-10)


def test_displaced_squeezed_mean_and_n():
    alpha = 0.2 + 0.1j
    r = 0.4
    st = GaussianState.displaced_squeezed(alpha, r=r)
    np.testing.assert_allclose(st.rbar[0], np.sqrt(2) * alpha.real)
    np.testing.assert_allclose(st.rbar[1], np.sqrt(2) * alpha.imag)
    np.testing.assert_allclose(det_cov(st), 0.25, atol=1e-12)
    # ⟨n⟩ = |α|² + sinh² r  (displaced squeezed vacuum, φ=0)
    expected_n = abs(alpha) ** 2 + np.sinh(r) ** 2
    np.testing.assert_allclose(mean_photon(st), expected_n, atol=1e-12)
    assert is_physical(st)


def test_tmsv_matches_gate_and_epr():
    r = 0.55
    st = GaussianState.tmsv(r)
    via_gate = two_mode_squeeze(GaussianState.vacuum(2), r, 0, 1)
    np.testing.assert_allclose(st.V, via_gate.V, atol=1e-12)
    # reduced mode 0 is thermal with nbar = sinh^2 r
    red = st.remove_mode(1)
    nbar = np.sinh(r) ** 2
    np.testing.assert_allclose(mean_photon(red), nbar, atol=1e-12)
    # EPR correlations (xxpp):
    # Var(x0 - x1) = e^{-2r}, Var(p0 + p1) = e^{-2r}
    # Var(x0 + x1) = e^{+2r}, Var(p0 - p1) = e^{+2r}
    Vx_m = st.V[0, 0] + st.V[1, 1] - 2 * st.V[0, 1]
    Vx_p = st.V[0, 0] + st.V[1, 1] + 2 * st.V[0, 1]
    Vp_p = st.V[2, 2] + st.V[3, 3] + 2 * st.V[2, 3]
    Vp_m = st.V[2, 2] + st.V[3, 3] - 2 * st.V[2, 3]
    np.testing.assert_allclose(Vx_m, np.exp(-2 * r), atol=1e-12)
    np.testing.assert_allclose(Vp_p, np.exp(-2 * r), atol=1e-12)
    np.testing.assert_allclose(Vx_p, np.exp(+2 * r), atol=1e-12)
    np.testing.assert_allclose(Vp_m, np.exp(+2 * r), atol=1e-12)
    assert is_physical(st)


def test_product_two_vacua():
    p = GaussianState.product(GaussianState.vacuum(1), GaussianState.vacuum(1))
    v2 = GaussianState.vacuum(2)
    np.testing.assert_allclose(p.V, v2.V)
    np.testing.assert_allclose(p.rbar, v2.rbar)


def test_product_single_is_deep_copy_embed():
    a = GaussianState.coherent(0.7)
    p = GaussianState.product(a)
    assert p is not a
    np.testing.assert_allclose(p.V, a.V)
    np.testing.assert_allclose(p.rbar, a.rbar)
    p.rbar[0] = 999.0
    assert a.rbar[0] != 999.0


def test_product_coherent_thermal_embed():
    a = GaussianState.coherent(0.3 + 0.0j, nmode=1)
    b = GaussianState.thermal(0.5, nmode=1)
    p = GaussianState.product(a, b)
    assert p.nmode == 2
    # mode 0 mean in global x0,p0
    np.testing.assert_allclose(p.rbar[0], a.rbar[0])
    np.testing.assert_allclose(p.rbar[2], a.rbar[1])  # p0 at index 2
    # mode 1 thermal block at x1=1, p1=3
    scale = 0.5 * (2 * 0.5 + 1)
    np.testing.assert_allclose(p.V[1, 1], scale)
    np.testing.assert_allclose(p.V[3, 3], scale)
    np.testing.assert_allclose(p.V[0, 0], 0.5)


def test_product_empty_raises():
    with pytest.raises(ValueError):
        GaussianState.product()


def test_physicality_vacuum_and_unphysical():
    assert is_physical(GaussianState.vacuum(2))
    validate_state(GaussianState.vacuum(1))
    # V = -I is wildly non-physical; constructor still accepts it
    bad = GaussianState(V=-np.eye(2), rbar=np.zeros(2))
    assert not is_physical(bad)
    assert not bad.is_physical()
    with pytest.raises(ValueError, match="non-physical"):
        validate_state(bad)
