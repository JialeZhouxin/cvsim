"""B1 Bosonic channels: amplifier / phase_noise K=1 vs Gaussian, validation."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.bosonic import (
    BosonicState,
    amplifier,
    displace,
    mean_photon,
    phase_noise,
)
from cvsim.gaussian import GaussianState
from cvsim.gaussian.channels import amplifier as g_amplifier
from cvsim.gaussian.channels import phase_noise as g_phase_noise

pytestmark = pytest.mark.phaseB1


def _wrapped(gs: GaussianState) -> BosonicState:
    return BosonicState.from_gaussian(gs)


def _g_2mode() -> GaussianState:
    gs = GaussianState.squeezed(0.4, nmode=2, mode=1)
    from cvsim.symplectic import d_displace

    return GaussianState(
        V=gs.V, rbar=gs.rbar + d_displace(2, 0.3 + 0.2j, 0)
    )


def _check_matches(b_out: BosonicState, g_out: GaussianState) -> None:
    assert b_out.n_components == 1
    c = b_out.components[0]
    np.testing.assert_allclose(c.V, g_out.V, atol=1e-10)
    np.testing.assert_allclose(c.rbar, g_out.rbar, atol=1e-10)
    assert abs(c.w - 1.0) < 1e-12


@pytest.mark.parametrize(
    "kwargs",
    [
        {"G": 1.5, "nbar": 0.0},
        {"G": 2.0, "nbar": 0.4},
        {"G": 1.1, "nbar": 1.0},
    ],
)
def test_amplifier_k1_matches_gaussian(kwargs):
    gs = _g_2mode()
    _check_matches(amplifier(_wrapped(gs), **kwargs), g_amplifier(gs, **kwargs))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"sigma": 0.3},
        {"sigma": 1.0},
        {"sigma": 0.0},
    ],
)
def test_phase_noise_k1_matches_gaussian(kwargs):
    gs = _g_2mode()
    _check_matches(phase_noise(_wrapped(gs), **kwargs), g_phase_noise(gs, **kwargs))


def test_amplifier_rejects_G_below_1():
    st = BosonicState.vacuum(1)
    with pytest.raises(ValueError):
        amplifier(st, 0.9)
    with pytest.raises(ValueError):
        amplifier(st, 1.0, nbar=-0.1)


def test_phase_noise_rejects_negative_sigma():
    st = BosonicState.vacuum(1)
    with pytest.raises(ValueError):
        phase_noise(st, -0.1)


def test_amplifier_G1_identity():
    st = BosonicState.vacuum(1)
    st2 = amplifier(st, 1.0, nbar=0.0)
    np.testing.assert_allclose(st2.components[0].V, st.components[0].V, atol=1e-12)
    np.testing.assert_allclose(
        st2.components[0].rbar, st.components[0].rbar, atol=1e-12
    )


def test_phase_noise_sigma0_identity():
    st = BosonicState.vacuum(1)
    st2 = phase_noise(st, 0.0)
    np.testing.assert_allclose(st2.components[0].V, st.components[0].V, atol=1e-12)
    np.testing.assert_allclose(
        st2.components[0].rbar, st.components[0].rbar, atol=1e-12
    )


def test_amplifier_mean_photon_closed_form():
    """Vacuum: ⟨n⟩ after amplifier(G, nbar) = (G−1)(nbar+1) (ħ=1)."""
    st = BosonicState.vacuum(1)
    assert mean_photon(amplifier(st, 1.0, nbar=0.0)) == pytest.approx(0.0, abs=1e-12)
    assert mean_photon(amplifier(st, 2.0, nbar=0.0)) == pytest.approx(1.0, abs=1e-12)
    assert mean_photon(amplifier(st, 2.0, nbar=1.0)) == pytest.approx(2.0, abs=1e-12)
    # trend sanity: gain increases mean photon
    n1 = mean_photon(amplifier(st, 1.5, nbar=0.0))
    n2 = mean_photon(amplifier(st, 2.5, nbar=0.0))
    assert n2 > n1


def test_amplifier_mode_specific_leaves_other_mode():
    gs = _g_2mode()
    out = amplifier(_wrapped(gs), 2.0, mode=1, nbar=0.0)
    c = out.components[0]
    # mode 0 block untouched: xxpp → indices (0, 2)
    np.testing.assert_allclose(
        c.V[np.ix_([0, 2], [0, 2])], gs.V[np.ix_([0, 2], [0, 2])], atol=1e-12
    )
    np.testing.assert_allclose(c.rbar[[0, 2]], gs.rbar[[0, 2]], atol=1e-12)


def test_phase_noise_damps_rbar():
    coh = displace(BosonicState.vacuum(1), 0.8 + 0.3j)
    sigma = 0.5
    out = phase_noise(coh, sigma)
    damp = np.exp(-sigma * sigma / 2.0)  # X = e^{−σ²/2}
    np.testing.assert_allclose(
        out.components[0].rbar, damp * coh.components[0].rbar, atol=1e-12
    )
