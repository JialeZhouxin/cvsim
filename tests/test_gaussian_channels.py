"""F-CHANNEL-GENERAL: apply_gaussian_channel + loss/amplifier/phase_noise."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.conventions import omega
from cvsim.gaussian import (
    GaussianState,
    amplifier,
    apply_gaussian_channel,
    apply_symplectic,
    displace,
    is_cp_channel,
    loss,
    mean_photon,
    phase_noise,
    squeeze,
    validate_channel,
)
from cvsim.symplectic import S_phase, S_squeeze


# --- core channel ----------------------------------------------------------


def test_channel_unitary_matches_apply_symplectic():
    st = GaussianState.displaced_squeezed(0.3 + 0.2j, r=0.4, phi=0.1)
    S = S_phase(1, 0.5)
    via = apply_gaussian_channel(st, S, np.zeros((2, 2)), validate=False)
    direct = apply_symplectic(st, S, validate=False)
    np.testing.assert_allclose(via.V, direct.V, atol=1e-12)
    np.testing.assert_allclose(via.rbar, direct.rbar, atol=1e-12)


def test_channel_shape_mismatch():
    st = GaussianState.vacuum(2)
    with pytest.raises(ValueError, match="must be"):
        apply_gaussian_channel(st, np.eye(2), np.zeros((4, 4)), validate=False)


def test_channel_d_displacement():
    st = GaussianState.vacuum(1)
    d = np.array([np.sqrt(2) * 0.5, 0.0])
    out = apply_gaussian_channel(st, np.eye(2), np.zeros((2, 2)), d=d, validate=False)
    np.testing.assert_allclose(out.rbar, d, atol=1e-12)
    np.testing.assert_allclose(out.V, 0.5 * np.eye(2), atol=1e-12)


# --- CP validation ---------------------------------------------------------


def test_cp_pure_loss_family_passes():
    for T in np.linspace(0.0, 1.0, 11):
        m = 1
        X = np.sqrt(T) * np.eye(2)
        Y = (1 - T) * 0.5 * np.eye(2)
        assert is_cp_channel(X, Y)


def test_cp_amplifier_family_passes():
    for G in [1.0, 1.5, 2.0, 5.0, 10.0]:
        X = np.sqrt(G) * np.eye(2)
        Y = (G - 1) * 0.5 * np.eye(2)
        assert is_cp_channel(X, Y)


def test_cp_phase_noise_family_passes():
    for sigma in [0.0, 0.3, 0.7, 1.0, 2.0]:
        damp = np.exp(-sigma * sigma / 2.0)
        X = damp * np.eye(2)
        Y = (1 - damp * damp) * 0.5 * np.eye(2)
        assert is_cp_channel(X, Y)


def test_cp_rejects_negative_Y():
    # Y negative on a diagonal => not CP
    X = np.eye(2)
    Y = -0.1 * np.eye(2)
    assert not is_cp_channel(X, Y)
    with pytest.raises(ValueError, match="non-CP"):
        validate_channel(X, Y)


def test_cp_rejects_unphysical_X():
    # X with huge scaling and no Y => violates CP
    X = 2.0 * np.eye(2)
    Y = np.zeros((2, 2))
    assert not is_cp_channel(X, Y)


def test_validate_true_rejects_non_cp():
    st = GaussianState.vacuum(1)
    with pytest.raises(ValueError, match="non-CP"):
        apply_gaussian_channel(st, 2.0 * np.eye(2), np.zeros((2, 2)))


def test_validate_false_escape_hatch():
    st = GaussianState.vacuum(1)
    # would fail validate=True; escape hatch lets it through
    out = apply_gaussian_channel(
        st, 2.0 * np.eye(2), np.zeros((2, 2)), validate=False
    )
    assert out.nmode == 1


# --- loss regression -------------------------------------------------------


def test_loss_t1_identity():
    st = displace(GaussianState.vacuum(1), 0.5 + 0.2j)
    st2 = loss(st, 1.0)
    np.testing.assert_allclose(st2.V, st.V, atol=1e-12)
    np.testing.assert_allclose(st2.rbar, st.rbar, atol=1e-12)


def test_loss_t0_vacuum():
    st = displace(GaussianState.vacuum(2), 0.8, mode=0)
    st = displace(st, 0.3j, mode=1)
    st2 = loss(st, 0.0)
    np.testing.assert_allclose(st2.V, 0.5 * np.eye(4), atol=1e-12)
    np.testing.assert_allclose(st2.rbar, 0.0, atol=1e-12)


def test_loss_coherent_photon_scales():
    alpha = 0.9 + 0.4j
    T = 0.35
    st = loss(displace(GaussianState.vacuum(1), alpha), T)
    assert abs(mean_photon(st) - T * abs(alpha) ** 2) < 1e-12


def test_loss_single_mode_leaves_other():
    st = displace(GaussianState.vacuum(2), 0.7, mode=0)
    st = displace(st, 0.5, mode=1)
    st2 = loss(st, 0.2, mode=0)
    assert abs(st2.rbar[1] - st.rbar[1]) < 1e-12
    assert abs(st2.rbar[3] - st.rbar[3]) < 1e-12
    assert abs(st2.rbar[0] - np.sqrt(0.2) * st.rbar[0]) < 1e-12


def test_loss_thermal_nbar():
    # loss into thermal env: coherent |α>, T, nbar => <n> = T|α|² + (1-T)nbar
    alpha = 0.6 + 0.0j
    T, nbar = 0.4, 1.5
    st = loss(displace(GaussianState.vacuum(1), alpha), T, nbar=nbar)
    expected = T * abs(alpha) ** 2 + (1 - T) * nbar
    assert abs(mean_photon(st) - expected) < 1e-12


def test_loss_rejects_bad_T_nbar():
    st = GaussianState.vacuum(1)
    with pytest.raises(ValueError, match="T must be"):
        loss(st, 1.5)
    with pytest.raises(ValueError, match="T must be"):
        loss(st, -0.1)
    with pytest.raises(ValueError, match="nbar"):
        loss(st, 0.5, nbar=-1.0)


def test_loss_mode_out_of_range():
    st = GaussianState.vacuum(2)
    with pytest.raises(IndexError):
        loss(st, 0.5, mode=5)


# --- amplifier -------------------------------------------------------------


def test_amplifier_g1_identity():
    st = displace(GaussianState.vacuum(1), 0.5 + 0.2j)
    st2 = amplifier(st, 1.0)
    np.testing.assert_allclose(st2.V, st.V, atol=1e-12)
    np.testing.assert_allclose(st2.rbar, st.rbar, atol=1e-12)


def test_amplifier_coherent_photon_scales():
    # amplifier adds noise to V: <n> = G|α|² + (G−1) (V grows by (G-1)/2)
    alpha = 0.5 + 0.3j
    G = 2.0
    st = amplifier(displace(GaussianState.vacuum(1), alpha), G)
    assert abs(mean_photon(st) - (G * abs(alpha) ** 2 + (G - 1))) < 1e-12


def test_amplifier_quantum_limited_adds_half():
    # vacuum -> amplifier(G, nbar=0) => <n> = G-1 (V grows to 0.5(2G-1))
    st = amplifier(GaussianState.vacuum(1), 3.0, nbar=0.0)
    assert abs(mean_photon(st) - (3.0 - 1)) < 1e-12


def test_amplifier_thermal_nbar():
    # vacuum -> amplifier(G, nbar) => <n> = (G-1)(nbar+1/2) + (G-1)/2
    # = (G-1)(nbar+1)  [V grows by G*0.5 + (G-1)(nbar+0.5); <n>=Vdiag-0.5]
    G, nbar = 2.0, 1.0
    st = amplifier(GaussianState.vacuum(1), G, nbar=nbar)
    expected = 0.5 * G + (G - 1) * (nbar + 0.5) - 0.5
    assert abs(mean_photon(st) - expected) < 1e-12


def test_amplifier_rejects_bad_G():
    st = GaussianState.vacuum(1)
    with pytest.raises(ValueError, match="G must be"):
        amplifier(st, 0.5)
    with pytest.raises(ValueError, match="nbar"):
        amplifier(st, 2.0, nbar=-0.1)


def test_amplifier_single_mode_leaves_other():
    st = displace(GaussianState.vacuum(2), 0.7, mode=0)
    st = displace(st, 0.5, mode=1)
    st2 = amplifier(st, 2.0, mode=0)
    assert abs(st2.rbar[1] - st.rbar[1]) < 1e-12
    assert abs(st2.rbar[3] - st.rbar[3]) < 1e-12
    assert abs(st2.rbar[0] - np.sqrt(2.0) * st.rbar[0]) < 1e-12


# --- phase noise (option B: rotation average) -----------------------------


def test_phase_noise_sigma0_identity():
    st = squeeze(GaussianState.vacuum(1), 0.5)
    st2 = phase_noise(st, 0.0)
    np.testing.assert_allclose(st2.V, st.V, atol=1e-12)
    np.testing.assert_allclose(st2.rbar, st.rbar, atol=1e-12)


def test_phase_noise_damps_squeezed_offdiag():
    # squeezed state with phi≠0 has off-diagonal V; phase noise damps it
    st = GaussianState.squeezed(0.8, phi=0.3)
    V0 = st.V.copy()
    assert abs(V0[0, 1]) > 1e-6  # precondition: has off-diagonal
    st2 = phase_noise(st, 0.5)
    # off-diagonal shrinks toward 0
    assert abs(st2.V[0, 1]) < abs(V0[0, 1])
    # still physical
    assert st2.is_physical()


def test_phase_noise_large_sigma_to_vacuum():
    # large sigma => damp -> 0, Y -> 0.5 I => vacuum covariance; rbar damped -> 0
    st = displace(GaussianState.vacuum(1), 0.5 + 0.2j)
    st2 = phase_noise(st, 5.0)
    np.testing.assert_allclose(st2.V, 0.5 * np.eye(2), atol=1e-6)
    np.testing.assert_allclose(st2.rbar, 0.0, atol=1e-5)


def test_phase_noise_rejects_negative_sigma():
    st = GaussianState.vacuum(1)
    with pytest.raises(ValueError, match="sigma"):
        phase_noise(st, -0.1)


def test_phase_noise_single_mode_leaves_other():
    st = displace(GaussianState.vacuum(2), 0.7, mode=0)
    st = displace(st, 0.5, mode=1)
    st2 = phase_noise(st, 0.4, mode=0)
    assert abs(st2.rbar[1] - st.rbar[1]) < 1e-12
    assert abs(st2.rbar[3] - st.rbar[3]) < 1e-12


# --- composition -----------------------------------------------------------


def test_channel_composition_law():
    # apply (X1,Y1) then (X2,Y2) == one shot (X2 X1, X2 Y1 X2ᵀ + Y2)
    st = GaussianState.displaced_squeezed(0.4 + 0.1j, r=0.3, phi=0.2)
    # two loss channels
    X1 = np.sqrt(0.7) * np.eye(2)
    Y1 = (1 - 0.7) * 0.5 * np.eye(2)
    X2 = np.sqrt(0.5) * np.eye(2)
    Y2 = (1 - 0.5) * 0.5 * np.eye(2)
    seq = apply_gaussian_channel(
        apply_gaussian_channel(st, X1, Y1, validate=False), X2, Y2, validate=False
    )
    X = X2 @ X1
    Y = X2 @ Y1 @ X2.T + Y2
    one = apply_gaussian_channel(st, X, Y, validate=False)
    np.testing.assert_allclose(seq.V, one.V, atol=1e-12)
    np.testing.assert_allclose(seq.rbar, one.rbar, atol=1e-12)


def test_loss_then_amplifier_compose():
    # loss(T) then amplifier(G): X = √G √T, Y = G(1-T)/2 + (G-1)/2
    st = displace(GaussianState.vacuum(1), 0.5)
    T, G = 0.6, 2.0
    seq = amplifier(loss(st, T), G)
    X = np.sqrt(G * T) * np.eye(2)
    Y = (G * (1 - T) / 2 + (G - 1) / 2) * np.eye(2)
    one = apply_gaussian_channel(st, X, Y, validate=False)
    np.testing.assert_allclose(seq.V, one.V, atol=1e-12)
    np.testing.assert_allclose(seq.rbar, one.rbar, atol=1e-12)


# --- multi-mode defaults ---------------------------------------------------


def test_loss_all_modes_default():
    st = displace(GaussianState.vacuum(2), 0.5, mode=0)
    st = displace(st, 0.3j, mode=1)
    st2 = loss(st, 0.5)  # mode=None => both
    # both modes scaled by √0.5
    assert abs(st2.rbar[0] - np.sqrt(0.5) * st.rbar[0]) < 1e-12
    assert abs(st2.rbar[3] - np.sqrt(0.5) * st.rbar[3]) < 1e-12


def test_amplifier_all_modes_default():
    st = displace(GaussianState.vacuum(2), 0.5, mode=0)
    st = displace(st, 0.3j, mode=1)
    st2 = amplifier(st, 4.0)  # mode=None => both
    assert abs(st2.rbar[0] - 2.0 * st.rbar[0]) < 1e-12
    assert abs(st2.rbar[3] - 2.0 * st.rbar[3]) < 1e-12
