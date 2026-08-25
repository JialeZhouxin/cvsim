"""Adversarial + researcher-level tests for commit a060b2a.

Amplifier / phase_noise / gaussian_channel circuit builders.
Corrected after initial run revealed 5 test assumptions were wrong.
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import (
    GaussianCircuit,
    GaussianState,
    det_cov,
    displace,
    is_cp_channel,
    is_physical,
    mean_photon,
    squeeze,
)

# =============================================================================
# 1. Amplifier — physical consistency
# =============================================================================

def test_amplifier_G1_on_vacuum():
    """G=1.0 on vacuum → still vacuum (V and rbar unchanged)."""
    c = GaussianCircuit(1)
    c.amplifier(0, G=1.0)
    st = c.run()
    np.testing.assert_allclose(st.V, 0.5 * np.eye(2), atol=1e-12)
    np.testing.assert_allclose(st.rbar, [0.0, 0.0], atol=1e-12)


def test_amplifier_G1_on_displaced_preserves_ratio():
    """G=1.0 preserves ratio of quadratures (rbar scales by √G=1)."""
    c = GaussianCircuit(1)
    c.displace(0, alpha=0.7 + 0.3j)
    c.amplifier(0, G=1.0)
    st = c.run()
    expected_rbar = np.array([np.sqrt(2) * 0.7, np.sqrt(2) * 0.3])
    np.testing.assert_allclose(st.rbar, expected_rbar, atol=1e-12)


def test_amplifier_G2_scales_rbar_by_sqrtG():
    """G=2.0 → rbar scaled by √2."""
    c = GaussianCircuit(1)
    c.displace(0, alpha=0.5 + 0.2j)
    c.amplifier(0, G=2.0)
    st = c.run()
    initial_rbar = np.array([np.sqrt(2) * 0.5, np.sqrt(2) * 0.2])
    expected_rbar = np.sqrt(2.0) * initial_rbar
    np.testing.assert_allclose(st.rbar, expected_rbar, atol=1e-10)


def test_amplifier_quantum_limited_nbar0():
    """nbar=0: minimum-added-noise amplifier.

    For coherent state α amplified by G:
    - Displacement energy: G·|α|² (rbar scaled by √G)
    - Quantum noise: Tr(V_q)/2 - 0.5 where V_q has eigenvalues giving G-1 photons
    Total: <n> = G·|α|² + (G - 1)
    """
    alpha = 1.0
    G = 3.0
    c = GaussianCircuit(1)
    c.displace(0, alpha=alpha)
    c.amplifier(0, G=G)
    st = c.run()
    expected_n = G * abs(alpha) ** 2 + (G - 1)
    np.testing.assert_allclose(mean_photon(st), expected_n, atol=1e-10)


def test_amplifier_nbar_nonzero():
    """Non-zero nbar: extra thermal noise."""
    G = 2.0
    nbar = 1.0
    c = GaussianCircuit(1)
    c.amplifier(0, G=G, nbar=nbar)
    st = c.run()
    V_diag = np.diag(st.V)
    # Thermal amp: V_diag = G·0.5 + (G-1)(nbar+0.5) per quad
    expected = G * 0.5 + (G - 1) * (nbar + 0.5)
    np.testing.assert_allclose(V_diag, [expected, expected], atol=1e-12)


def test_amplifier_G_lt_1_rejected():
    c = GaussianCircuit(1)
    c.amplifier(0, G=0.5)
    with pytest.raises(ValueError):
        c.run()


def test_amplifier_nbar_negative_rejected():
    c = GaussianCircuit(1)
    c.amplifier(0, G=2.0, nbar=-0.1)
    with pytest.raises(ValueError):
        c.run()


def test_amplifier_mode_out_of_range():
    c = GaussianCircuit(1)
    c.amplifier(5, G=2.0)
    with pytest.raises(IndexError):
        c.run()


def test_amplifier_all_modes_vs_individual():
    c1 = GaussianCircuit(3)
    for i in range(3):
        c1.displace(i, alpha=0.3 + 0.1j * i)
    c1.amplifier(G=2.5)

    c2 = GaussianCircuit(3)
    for i in range(3):
        c2.displace(i, alpha=0.3 + 0.1j * i)
    for i in range(3):
        c2.amplifier(i, G=2.5)

    st1, st2 = c1.run(), c2.run()
    np.testing.assert_allclose(st1.V, st2.V, atol=1e-12)
    np.testing.assert_allclose(st1.rbar, st2.rbar, atol=1e-12)


def test_amplifier_preserves_physicality():
    for G in [1.0, 1.1, 2.0, 5.0, 10.0]:
        c = GaussianCircuit(2)
        c.squeeze(0, r=0.8)
        c.squeeze(1, r=0.6)
        c.amplifier(G=G, nbar=0.5)
        st = c.run()
        assert is_physical(st), f"unphysical at G={G}"


def test_amplifier_on_squeezed_after_measure():
    """Measure one mode, amplify remaining squeezed mode using mode=None."""
    c = GaussianCircuit(2)
    c.squeeze(0, r=0.5)
    c.measure_homodyne(1, phi=0, name='m')  # remove mode 1 (unrelated)
    c.amplifier(mode=None, G=2.0)  # all remaining: just mode 0
    st, _ = c.run(rng=np.random.default_rng(42))
    assert st.nmode == 1
    assert is_physical(st)
    # Mode 0 is amplified squeezed vacuum: V_diag ≈ [2*0.184+0.5, 2*1.359+0.5]
    np.testing.assert_allclose(np.diag(st.V)[:2],
                               [2 * np.exp(-1.0) / 2 + 0.5,
                                2 * np.exp(1.0) / 2 + 0.5],
                               atol=1e-10)
    assert mean_photon(st) > 1.0


def test_amplifier_no_measurement_returns_state():
    """No measurement → run() returns GaussianState (backward compat)."""
    c = GaussianCircuit(1)
    c.amplifier(0, G=2.0)
    st = c.run()
    assert not isinstance(st, tuple)
    assert st.nmode == 1


# =============================================================================
# 2. Phase noise — physical consistency
# =============================================================================

def test_phase_noise_sigma0_identity():
    """sigma=0 → identity."""
    st0 = squeeze(GaussianState.vacuum(1), 0.7)
    c = GaussianCircuit(1)
    c.squeeze(0, r=0.7)
    c.phase_noise(0, sigma=0.0)
    st = c.run()
    np.testing.assert_allclose(st.V, st0.V, atol=1e-12)
    np.testing.assert_allclose(st.rbar, st0.rbar, atol=1e-12)


def test_phase_noise_attenuates_rbar():
    """Phase noise attenuates rbar by damp = exp(-sigma^2/2)."""
    c = GaussianCircuit(1)
    c.displace(0, alpha=0.5 + 0.3j)
    c.phase_noise(0, sigma=1.0)
    st = c.run()
    initial_rbar = np.array([np.sqrt(2) * 0.5, np.sqrt(2) * 0.3])
    damp = np.exp(-1.0 ** 2 / 2.0)
    expected_rbar = damp * initial_rbar
    np.testing.assert_allclose(st.rbar, expected_rbar, atol=1e-12)


def test_phase_noise_converges_to_isotropic():
    """Large sigma → isotropic covariance V = 0.5·I."""
    c = GaussianCircuit(1)
    c.squeeze(0, r=1.0)
    c.phase_noise(0, sigma=10.0)
    st = c.run()
    np.testing.assert_allclose(np.diag(st.V), [0.5, 0.5], atol=0.01)


def test_phase_noise_negative_rejected():
    c = GaussianCircuit(1)
    c.phase_noise(0, sigma=-0.1)
    with pytest.raises(ValueError):
        c.run()


def test_phase_noise_all_modes_vs_individual():
    c1 = GaussianCircuit(2)
    c1.squeeze(0, r=0.5)
    c1.squeeze(1, r=0.3)
    c1.phase_noise(sigma=0.8)

    c2 = GaussianCircuit(2)
    c2.squeeze(0, r=0.5)
    c2.squeeze(1, r=0.3)
    c2.phase_noise(0, sigma=0.8)
    c2.phase_noise(1, sigma=0.8)

    st1, st2 = c1.run(), c2.run()
    np.testing.assert_allclose(st1.V, st2.V, atol=1e-12)


def test_phase_noise_is_physical():
    for sigma in [0.0, 0.1, 0.5, 1.0, 3.0, 10.0]:
        c = GaussianCircuit(1)
        c.squeeze(0, r=0.8)
        c.phase_noise(0, sigma=sigma)
        st = c.run()
        assert is_physical(st), f"unphysical at sigma={sigma}"


def test_phase_noise_on_squeezed_after_measure():
    """Measure one independent mode, apply phase_noise to remaining via mode=None.

    Physics: homodyne on unentangled mode 1 doesn't affect mode 0's V.
    Phase noise then applies: V_new = damp^2 · V_old + (1-damp^2)·0.5·I
    """
    c = GaussianCircuit(2)
    c.squeeze(0, r=0.8)
    c.measure_homodyne(1, phi=0, name='m')
    c.phase_noise(mode=None, sigma=0.5)
    st, _ = c.run(rng=np.random.default_rng(42))
    assert st.nmode == 1
    assert is_physical(st)
    # Independent modes: measuring mode 1 does NOT change mode 0's covariance
    # Same result as single-mode squeeze + phase_noise
    c_ref = GaussianCircuit(1)
    c_ref.squeeze(0, r=0.8)
    c_ref.phase_noise(0, sigma=0.5)
    st_ref = c_ref.run()
    np.testing.assert_allclose(np.diag(st.V), np.diag(st_ref.V)[:2], atol=1e-12)


def test_phase_noise_no_measurement_returns_state():
    c = GaussianCircuit(1)
    c.phase_noise(0, sigma=0.5)
    st = c.run()
    assert not isinstance(st, tuple)


# =============================================================================
# 3. Gaussian channel — CP validation
# =============================================================================

def test_gaussian_channel_noncp_raises():
    X = 0.1 * np.eye(2)
    Y = 1e-6 * np.eye(2)
    c = GaussianCircuit(1)
    c.gaussian_channel(X, Y, validate=True)
    with pytest.raises(ValueError, match="non-CP"):
        c.run()


def test_gaussian_channel_noncp_novalidate_silent():
    X = 0.1 * np.eye(2)
    Y = 1e-6 * np.eye(2)
    c = GaussianCircuit(1)
    c.gaussian_channel(X, Y, validate=False)
    st = c.run()
    assert st.nmode == 1


def test_gaussian_channel_identity():
    st0 = displace(GaussianState.vacuum(1), 0.5)
    c = GaussianCircuit(1)
    c.displace(0, alpha=0.5)
    c.gaussian_channel(np.eye(2), np.zeros((2, 2)), validate=False)
    st = c.run()
    np.testing.assert_allclose(st.V, st0.V, atol=1e-12)
    np.testing.assert_allclose(st.rbar, st0.rbar, atol=1e-12)


def test_gaussian_channel_shape_odd_rejected():
    with pytest.raises(ValueError, match="2m"):
        GaussianCircuit(1).gaussian_channel(np.eye(3), np.zeros((3, 3)))


def test_gaussian_channel_shape_mismatch_xy():
    with pytest.raises(ValueError, match="Y shape"):
        GaussianCircuit(1).gaussian_channel(np.eye(2), np.zeros((4, 4)))


def test_gaussian_channel_d_shape_mismatch():
    with pytest.raises(ValueError, match="d must be"):
        GaussianCircuit(1).gaussian_channel(np.eye(2), np.zeros((2, 2)), d=np.zeros(4))


def test_gaussian_channel_1d_array_rejected():
    with pytest.raises(ValueError, match="2m"):
        GaussianCircuit(1).gaussian_channel(np.zeros(2), np.zeros(2))


def test_gaussian_channel_non_square_rejected():
    with pytest.raises(ValueError, match="2m"):
        GaussianCircuit(1).gaussian_channel(np.zeros((2, 4)), np.zeros((2, 4)))


def test_gaussian_channel_valid_cp_passes():
    T = 0.7
    X = np.sqrt(T) * np.eye(2)
    Y = (1 - T) * 0.5 * np.eye(2)
    assert is_cp_channel(X, Y)
    c = GaussianCircuit(1)
    c.gaussian_channel(X, Y, validate=True)
    st = c.run()
    assert is_physical(st)


def test_gaussian_channel_d_2mode():
    d = np.array([0.5, -0.3, 0.1, 0.2])
    c = GaussianCircuit(2)
    c.gaussian_channel(np.eye(4), np.zeros((4, 4)), d=d, validate=False)
    st = c.run()
    np.testing.assert_allclose(st.rbar, d, atol=1e-12)
    np.testing.assert_allclose(st.V, 0.5 * np.eye(4), atol=1e-12)


def test_gaussian_channel_d_with_XY():
    X = np.sqrt(0.5) * np.eye(2)
    Y = 0.25 * np.eye(2)
    d = np.array([1.0, -1.0])
    c = GaussianCircuit(1)
    c.displace(0, alpha=0.5)
    c.gaussian_channel(X, Y, d=d, validate=False)
    st = c.run()
    rbar_old = np.array([np.sqrt(2) * 0.5, 0.0])
    expected_rbar = X @ rbar_old + d
    np.testing.assert_allclose(st.rbar, expected_rbar, atol=1e-12)


# =============================================================================
# 4. Gaussian channel — composition behavior
# =============================================================================

def test_loss_then_amp_not_identity():
    """loss(T=0.5) + amp(G=2.0) ≠ identity (added quantum noise)."""
    T, G = 0.5, 2.0
    c = GaussianCircuit(1)
    c.displace(0, alpha=1.0)
    c.loss(0, T=T)
    c.amplifier(0, G=G)
    st = c.run()
    assert det_cov(st) > 0.25


def test_amp_then_loss_not_identity():
    c = GaussianCircuit(1)
    c.amplifier(0, G=2.0)
    c.loss(0, T=0.5)
    st = c.run()
    assert det_cov(st) > 0.25


def test_chain_noise_monotonic():
    c = GaussianCircuit(1)
    c.squeeze(0, r=0.5)
    st0 = c.run()
    det0 = det_cov(st0)

    c2 = GaussianCircuit(1)
    c2.squeeze(0, r=0.5)
    c2.loss(0, T=0.9)
    st1 = c2.run()
    det1 = det_cov(st1)

    c3 = GaussianCircuit(1)
    c3.squeeze(0, r=0.5)
    c3.loss(0, T=0.9)
    c3.amplifier(0, G=1.2)
    st2 = c3.run()
    det2 = det_cov(st2)

    assert det1 >= det0
    assert det2 >= det1


# =============================================================================
# 5. Mode mapping after measurement
# =============================================================================

def test_amplifier_on_measured_mode_raises():
    c = GaussianCircuit(2)
    c.measure_homodyne(0, phi=0, name='m')
    c.amplifier(0, G=2.0)  # logical mode 0 has been removed
    with pytest.raises(ValueError, match="measured/removed"):
        c.run()


def test_phase_noise_on_measured_mode_raises():
    c = GaussianCircuit(2)
    c.measure_homodyne(0, phi=0, name='m')
    c.phase_noise(0, sigma=0.5)
    with pytest.raises(ValueError, match="measured/removed"):
        c.run()


def test_amp_mode_index_shift_correctly():
    """After removing mode 1, operating on 'mode 0' still works on original mode 0."""
    c = GaussianCircuit(2)
    c.squeeze(0, r=0.3)  # mode 0 squeezed
    c.measure_homodyne(1, phi=0, name='m')  # remove mode 1
    c.amplifier(0, G=2.0)  # operate on original mode 0
    st, _ = c.run(rng=np.random.default_rng(42))
    assert st.nmode == 1
    assert is_physical(st)
    assert mean_photon(st) > 0.5


# =============================================================================
# 6. ParamRef interaction with channels
# =============================================================================

def test_amplifier_param_G():
    c = GaussianCircuit(1)
    c.amplifier(0, G='g')
    st1 = c.run(g=1.5)
    st2 = c.run(g=3.0)
    assert mean_photon(st2) > mean_photon(st1)


def test_phase_noise_param_sigma():
    """Larger sigma makes V more isotropic (diagonal entries converge)."""
    c = GaussianCircuit(1)
    c.squeeze(0, r=0.5)
    c.phase_noise(0, sigma='s')
    st0 = c.run(s=0.0)  # no PN: anisotropic squeezed vacuum
    st1 = c.run(s=3.0)  # large PN: nearly isotropic
    # Diagonal ratio converges toward 1 (isotropic)
    ratio0 = max(np.diag(st0.V)) / min(np.diag(st0.V))
    ratio1 = max(np.diag(st1.V)) / min(np.diag(st1.V))
    assert ratio1 < ratio0


def test_amplifier_missing_param_raises():
    c = GaussianCircuit(1)
    c.amplifier(0, G='g')
    with pytest.raises(ValueError, match="g"):
        c.run()


# =============================================================================
# 7. Builder contracts
# =============================================================================

def test_amp_phase_amp_channel_builder_returns_self():
    c = GaussianCircuit(1)
    assert c.amplifier(0, G=2.0) is c
    assert c.phase_noise(0, sigma=0.1) is c
    assert c.gaussian_channel(np.eye(2), np.zeros((2, 2))) is c


def test_circuit_len_includes_channels():
    c = GaussianCircuit(1)
    c.amplifier(0, G=2.0)
    assert len(c) == 1
    c.phase_noise(0, sigma=0.1)
    assert len(c) == 2
    c.gaussian_channel(np.eye(2), np.zeros((2, 2)))
    assert len(c) == 3


def test_repr_shows_channel_ops():
    c = GaussianCircuit(1)
    c.amplifier(0, G=2.0)
    c.phase_noise(0, sigma=0.1)
    c.gaussian_channel(np.eye(2), np.zeros((2, 2)), validate=False)
    s = repr(c)
    assert 'amplifier' in s
    assert 'phase_noise' in s
    assert 'gaussian_channel' in s


def test_all_modes_large_circuit():
    """mode=None on 5-mode circuit."""
    n = 5
    c = GaussianCircuit(n)
    for i in range(n):
        c.displace(i, alpha=0.3)
    c.amplifier(G=2.0)
    c.phase_noise(sigma=0.3)
    st = c.run()
    assert st.nmode == n
    assert is_physical(st)


def test_gaussian_channel_after_measure_on_remaining_modes():
    """(X,Y) sized for remaining nmode works after measure."""
    X = np.sqrt(0.5) * np.eye(2)
    Y = 0.25 * np.eye(2)
    c = GaussianCircuit(2)
    c.squeeze(0, r=0.4)
    c.measure_homodyne(1, phi=0.0, name='m')
    c.gaussian_channel(X, Y, validate=False)
    st, res = c.run(rng=np.random.default_rng(1))
    assert st.nmode == 1
    assert 'm' in res
    assert is_physical(st)


def test_full_size_channel_after_measure_fails():
    X = np.eye(4)
    Y = np.zeros((4, 4))
    c = GaussianCircuit(2)
    c.squeeze(0, r=0.3)
    c.measure_homodyne(1, phi=0.0, name='m')
    c.gaussian_channel(X, Y, validate=False)
    with pytest.raises(ValueError, match="does not match"):
        c.run(rng=np.random.default_rng(0))
