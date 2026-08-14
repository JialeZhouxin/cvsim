"""B1 Bosonic component-wise gates."""

from __future__ import annotations

import numpy as np
import pytest

import cvsim.gaussian as g
from cvsim.bosonic import (
    coherent,
    cx,
    cz,
    displace,
    even_cat,
    fourier,
    interferometer,
    mach_zehnder,
    phase,
    weight_sum,
)
from cvsim.bosonic.state import BosonicState, Component
from cvsim.conventions import vacuum_cov
from cvsim.gaussian.gates import (
    cx as g_cx,
    cz as g_cz,
    fourier as g_fourier,
    interferometer as g_interferometer,
    mach_zehnder as g_mz,
)
from cvsim.symplectic import S_CX, S_CZ, d_displace, is_symplectic


def test_cat_phase_keeps_weight_sum_and_rotates():
    st = even_cat(0.8)
    theta = 0.5
    st2 = phase(st, theta)
    assert abs(weight_sum(st2) - 1.0) < 1e-12
    # diagonal peaks (卤rx, 0) rotate in (x,p)
    r0 = st.components[0].rbar
    r0p = st2.components[0].rbar
    c, s = np.cos(theta), np.sin(theta)
    expect = np.array([c * r0[0] - s * r0[1], s * r0[0] + c * r0[1]])
    assert np.allclose(r0p, expect, atol=1e-12)


def test_displace_single_component_weights():
    vac = BosonicState(
        components=[Component(V=vacuum_cov(1), rbar=np.zeros(2, dtype=complex), w=1.0)]
    )
    st = displace(vac, 0.3 + 0.2j)
    assert abs(weight_sum(st) - 1.0) < 1e-12
    rx = np.sqrt(2) * 0.3
    rp = np.sqrt(2) * 0.2
    assert abs(st.components[0].rbar[0] - rx) < 1e-12
    assert abs(st.components[0].rbar[1] - rp) < 1e-12


# ---------------------------------------------------------------------------
# B1: full Gaussian gate set (fourier/mz/cz/cx/interferometer), K=1 alignment
# ---------------------------------------------------------------------------


def _g_2mode():
    gs = g.GaussianState.squeezed(0.4, nmode=2, mode=1)
    return g.GaussianState(V=gs.V, rbar=gs.rbar + d_displace(2, 0.3 + 0.2j, 0))


def _check_matches(b_out, g_out):
    assert b_out.n_components == 1
    c = b_out.components[0]
    np.testing.assert_allclose(c.V, g_out.V, atol=1e-10)
    np.testing.assert_allclose(c.rbar, g_out.rbar, atol=1e-10)
    assert abs(c.w - 1.0) < 1e-12


@pytest.mark.phaseB1
def test_fourier_k1_matches_gaussian():

    gs = _g_2mode()
    bs = BosonicState.from_gaussian(gs)
    _check_matches(fourier(bs, mode=0), g_fourier(gs, mode=0))
    _check_matches(fourier(bs, mode=1), g_fourier(gs, mode=1))


@pytest.mark.phaseB1
def test_fourier_equals_phase_pi_half():

    gs = _g_2mode()
    bs = BosonicState.from_gaussian(gs)
    np.testing.assert_allclose(
        fourier(bs, mode=0).components[0].V,
        phase(bs, 0.5 * np.pi, mode=0).components[0].V,
        atol=1e-12,
    )


@pytest.mark.phaseB1
@pytest.mark.parametrize("theta,phi", [(0.3, 0.0), (0.4, 0.2), (1.1, -0.5)])
def test_mach_zehnder_k1_matches_gaussian(theta, phi):

    gs = _g_2mode()
    bs = BosonicState.from_gaussian(gs)
    _check_matches(mach_zehnder(bs, 0, 1, theta, phi), g_mz(gs, 0, 1, theta, phi))


@pytest.mark.phaseB1
@pytest.mark.parametrize("weight", [0.3, 1.0, -0.7])
def test_cz_k1_matches_gaussian_and_symplectic(weight):

    gs = _g_2mode()
    bs = BosonicState.from_gaussian(gs)
    _check_matches(cz(bs, weight, 0, 1), g_cz(gs, weight, 0, 1))
    assert is_symplectic(S_CZ(2, weight, 0, 1))


@pytest.mark.phaseB1
@pytest.mark.parametrize("weight", [0.3, 1.0, -0.7])
def test_cx_k1_matches_gaussian_and_symplectic(weight):

    gs = _g_2mode()
    bs = BosonicState.from_gaussian(gs)
    _check_matches(cx(bs, weight, 0, 1), g_cx(gs, weight, 0, 1))
    assert is_symplectic(S_CX(2, weight, 0, 1))


@pytest.mark.phaseB1
def test_interferometer_k1_matches_gaussian():

    gs = _g_2mode()
    bs = BosonicState.from_gaussian(gs)
    U = np.array([[1.0, 1j], [1j, 1.0]]) / np.sqrt(2.0)
    _check_matches(interferometer(bs, U), g_interferometer(gs, U))


@pytest.mark.phaseB1
def test_interferometer_rejects_non_unitary():

    bs = BosonicState.from_gaussian(_g_2mode())
    U = np.array([[1.0, 2.0], [0.0, 1.0]])
    with pytest.raises(ValueError):
        interferometer(bs, U)


@pytest.mark.phaseB1
def test_interferometer_validate_u_false_escape_hatch():

    bs = BosonicState.from_gaussian(_g_2mode())
    U = np.eye(2)
    out = interferometer(bs, U, validate_u=False)
    np.testing.assert_allclose(
        out.components[0].V, bs.components[0].V, atol=1e-12
    )


@pytest.mark.phaseB1
def test_coherent_factory():

    st = coherent(0.3 + 0.2j, nmode=2, mode=1)
    assert st.nmode == 2 and st.n_components == 1
    c = st.components[0]
    np.testing.assert_allclose(c.V, vacuum_cov(2), atol=1e-12)
    expect = np.zeros(4, dtype=complex)
    expect[1] = np.sqrt(2.0) * 0.3
    expect[3] = np.sqrt(2.0) * 0.2
    np.testing.assert_allclose(c.rbar, expect, atol=1e-12)
    assert abs(c.w - 1.0) < 1e-12
    with pytest.raises(IndexError):
        coherent(0.1, nmode=1, mode=1)
    with pytest.raises(ValueError):
        coherent(0.1, nmode=0)
