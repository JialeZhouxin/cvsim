"""Parameterized GaussianCircuit acceptance tests (L2+L3+L4)."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import (
    GaussianCircuit,
    GaussianState,
    ParamRef,
    amplifier,
    apply_gaussian_channel,
    det_cov,
    displace,
    loss,
    mean_photon,
    phase_noise,
    squeeze,
)


def test_basic_parameter_scan():
    """Same circuit, different parameters produce different results."""
    c = GaussianCircuit(2)
    c.squeeze(0, r="r1")
    c.cz(0, 1, weight="g")

    n0 = mean_photon(c.run(r1=0.5, g=0.0))
    n1 = mean_photon(c.run(r1=0.5, g=0.5))
    assert n1 > n0  # CZ adds photons


def test_fixed_vs_param():
    """Fixed parameters are baked in; symbolic are resolved at run."""
    c = GaussianCircuit(1)
    c.squeeze(0, r="r1")
    c.phase(0, theta=0.5)  # fixed
    st = c.run(r1=0.3)
    # After phase rotation, V should have off-diagonal x-p correlation
    assert abs(st.V[0, 1]) > 1e-6


def test_loss_channel():
    """Loss makes state mixed (det V > (1/4)^nmode)."""
    c = GaussianCircuit(1)
    c.squeeze(0, r=0.5)
    c.loss(0, T="trans")
    st = c.run(trans=0.8)
    assert det_cov(st) > 0.25  # mixed


def test_missing_param_raises():
    """Missing symbolic parameter raises ValueError with param name."""
    c = GaussianCircuit(2)
    c.squeeze(0, r="r1")
    with pytest.raises(ValueError, match="r1"):
        c.run()


def test_chain_builder():
    """Builder methods return self for chaining."""
    c = GaussianCircuit(3)
    result = (
        c.squeeze(0, r=0.5)
        .cz(0, 1, weight=0.3)
        .beamsplitter(1, 2, theta=np.pi / 4)
        .cx(0, 2, weight="g")
        .loss(0, T=0.9)
    )
    assert result is c
    assert len(c) == 5


def test_repr_shows_fixed_and_param():
    """repr distinguishes fixed values from symbolic params."""
    c = GaussianCircuit(1)
    c.squeeze(0, r="r1")
    c.phase(0, theta=0.5)
    s = repr(c)
    assert "${r1}" in s
    assert "theta=0.5" in s


def test_invalid_nmode():
    with pytest.raises(ValueError):
        GaussianCircuit(0)


def test_three_mode_cz():
    """CZ on modes 0,2 leaves mode 1 untouched."""
    c = GaussianCircuit(3)
    c.cz(0, 2, weight=0.5)
    st = c.run()
    n0 = mean_photon(st, mode=0)
    n1 = mean_photon(st, mode=1)
    n2 = mean_photon(st, mode=2)
    assert n0 > 0 and n2 > 0
    assert n1 == 0.0


# -- L3: circuit composition ---------------------------------------------


def test_circuit_add_returns_new():
    c1 = GaussianCircuit(2)
    c1.squeeze(0, r=0.5)
    c2 = GaussianCircuit(2)
    c2.cz(0, 1, weight=0.3)
    c3 = c1 + c2
    assert len(c3) == 2
    assert len(c1) == 1  # unchanged
    assert len(c2) == 1  # unchanged


def test_circuit_iadd_mutates():
    c1 = GaussianCircuit(2)
    c1.squeeze(0, r=0.5)
    c2 = GaussianCircuit(2)
    c2.cz(0, 1, weight=0.3)
    c1 += c2
    assert len(c1) == 2


def test_add_nmode_mismatch():
    with pytest.raises(ValueError, match="nmode mismatch"):
        GaussianCircuit(2) + GaussianCircuit(3)


def test_iadd_nmode_mismatch():
    c = GaussianCircuit(2)
    with pytest.raises(ValueError, match="nmode mismatch"):
        c += GaussianCircuit(3)


# -- L4: measurement + feedforward ---------------------------------------


def test_measurement_removes_mode():
    """After measure_homodyne, nmode decreases by 1."""
    c = GaussianCircuit(2)
    c.squeeze(1, r=0.5)
    c.measure_homodyne(1, phi=0, name="m")
    rng = np.random.default_rng(42)
    st, res = c.run(rng=rng)
    assert st.nmode == 1
    assert "m" in res


def test_measurement_removes_correct_mode():
    """Measuring mode 0 shifts mode 1 to physical 0."""
    c = GaussianCircuit(2)
    c.squeeze(0, r=0.3)
    c.squeeze(1, r=0.5)
    c.measure_homodyne(0, phi=0, name="m0")
    # remaining mode is originally mode 1 (squeezed with r=0.5)
    rng = np.random.default_rng(1)
    st, _ = c.run(rng=rng)
    n = mean_photon(st)
    # mode 1 squeezed r=0.5 => <n> = sinh²(0.5) ≈ 0.267
    assert abs(n - np.sinh(0.5) ** 2) < 1e-6


def test_feedforward_displace():
    """ParamRef feeds measurement into displacement."""
    rng = np.random.default_rng(42)
    c = GaussianCircuit(2)
    c.squeeze(1, r=0.5)
    c.cz(0, 1, weight=1.0)
    c.measure_homodyne(1, phi=np.pi / 2, name="mp")
    c.displace(0, alpha=ParamRef("mp", gain=0.5))
    st, res = c.run(rng=rng)
    assert st.nmode == 1
    # gain=0 produces different mean (no feedback)
    rng2 = np.random.default_rng(42)
    c2 = GaussianCircuit(2)
    c2.squeeze(1, r=0.5)
    c2.cz(0, 1, weight=1.0)
    c2.measure_homodyne(1, phi=np.pi / 2, name="mp")
    c2.displace(0, alpha=ParamRef("mp", gain=0.0))
    st0, res0 = c2.run(rng=rng2)
    assert res["mp"] == res0["mp"]  # same measurement
    # displacement in xxpp: d[0] = √2·Re(alpha) = √2·mp·0.5
    assert abs((st.rbar[0] - st0.rbar[0]) - res["mp"] * 0.5 * np.sqrt(2)) < 1e-10


def test_multiple_measurements():
    """Two sequential measurements both remove modes."""
    c = GaussianCircuit(3)
    c.squeeze(0, r=0.3)
    c.squeeze(1, r=0.5)
    c.measure_homodyne(1, phi=0, name="m1")
    c.measure_homodyne(0, phi=np.pi / 2, name="m2")
    rng = np.random.default_rng(7)
    st, res = c.run(rng=rng)
    assert st.nmode == 1
    assert len(res) == 2
    assert "m1" in res and "m2" in res


def test_no_measurement_returns_state():
    """Backward compat: no measurement → run() returns GaussianState."""
    c = GaussianCircuit(1)
    c.squeeze(0, r=0.5)
    st = c.run()
    assert not isinstance(st, tuple)
    assert st.nmode == 1


def test_paramref_missing_measurement():
    """ParamRef referencing unmeasured name raises."""
    c = GaussianCircuit(1)
    c.displace(0, alpha=ParamRef("unknown", 0.5))
    with pytest.raises(ValueError, match="unknown"):
        c.run()


def test_repr_shows_measurement_and_paramref():
    """repr shows measurement name and ParamRef source*gain."""
    c = GaussianCircuit(2)
    c.squeeze(1, r=0.5)
    c.measure_homodyne(1, phi=0, name="mx")
    c.displace(0, alpha=ParamRef("mx", 0.5))
    s = repr(c)
    assert "measure_homodyne" in s
    assert "name=mx" in s
    assert "${mx}*0.5" in s


# --- channel builders (amplifier / phase_noise / gaussian_channel) ---------


def test_circuit_amplifier_matches_functional():
    c = GaussianCircuit(1)
    c.displace(0, alpha=0.5 + 0.2j)
    c.amplifier(0, G=2.0)
    st = c.run()
    direct = amplifier(displace(GaussianState.vacuum(1), 0.5 + 0.2j), 2.0, mode=0)
    np.testing.assert_allclose(st.V, direct.V, atol=1e-12)
    np.testing.assert_allclose(st.rbar, direct.rbar, atol=1e-12)
    assert mean_photon(st) > 0


def test_circuit_amplifier_all_modes_and_param():
    c = GaussianCircuit(2)
    c.displace(0, alpha=0.4)
    c.displace(1, alpha=0.3j)
    c.amplifier(G="gain")  # mode=None → all
    st = c.run(gain=4.0)
    base = displace(GaussianState.vacuum(2), 0.4, mode=0)
    base = displace(base, 0.3j, mode=1)
    direct = amplifier(base, 4.0)
    np.testing.assert_allclose(st.V, direct.V, atol=1e-12)
    np.testing.assert_allclose(st.rbar, direct.rbar, atol=1e-12)


def test_circuit_phase_noise_matches_functional():
    c = GaussianCircuit(1)
    c.squeeze(0, r=0.6)
    c.phase_noise(0, sigma=0.4)
    st = c.run()
    direct = phase_noise(squeeze(GaussianState.vacuum(1), 0.6), 0.4)
    np.testing.assert_allclose(st.V, direct.V, atol=1e-12)


def test_circuit_phase_noise_param_scan():
    c = GaussianCircuit(1)
    c.squeeze(0, r=0.5)
    c.phase_noise(0, sigma="s")
    st0 = c.run(s=0.0)
    st1 = c.run(s=1.0)
    # larger phase noise → closer to vacuum diag
    assert abs(st1.V[0, 0] - 0.5) < abs(st0.V[0, 0] - 0.5) or np.isclose(st0.V[0, 0], st1.V[0, 0])
    assert st1.is_physical()


def test_circuit_gaussian_channel_matches_functional():
    T = 0.4
    X = np.sqrt(T) * np.eye(2)
    Y = (1 - T) * 0.5 * np.eye(2)
    c = GaussianCircuit(1)
    c.displace(0, alpha=0.7)
    c.gaussian_channel(X, Y)
    st = c.run()
    direct = apply_gaussian_channel(displace(GaussianState.vacuum(1), 0.7), X, Y, validate=False)
    np.testing.assert_allclose(st.V, direct.V, atol=1e-12)
    np.testing.assert_allclose(st.rbar, direct.rbar, atol=1e-12)


def test_circuit_gaussian_channel_with_d():
    d = np.array([0.3, -0.1])
    c = GaussianCircuit(1)
    c.gaussian_channel(np.eye(2), np.zeros((2, 2)), d=d, validate=False)
    st = c.run()
    np.testing.assert_allclose(st.rbar, d, atol=1e-12)


def test_circuit_gaussian_channel_rejects_after_measure():
    """Full (X,Y) sized for original nmode fails after mode removal."""
    X = np.eye(4)
    Y = np.zeros((4, 4))
    c = GaussianCircuit(2)
    c.squeeze(0, r=0.3)
    c.measure_homodyne(1, phi=0.0, name="m")
    c.gaussian_channel(X, Y, validate=False)
    with pytest.raises(ValueError, match="does not match"):
        c.run(rng=np.random.default_rng(0))


def test_circuit_gaussian_channel_ok_on_remaining_modes():
    """(X,Y) sized for remaining nmode after measure works."""
    X = np.sqrt(0.5) * np.eye(2)
    Y = 0.25 * np.eye(2)
    c = GaussianCircuit(2)
    c.squeeze(0, r=0.4)
    c.measure_homodyne(1, phi=0.0, name="m")
    c.gaussian_channel(X, Y, validate=False)
    st, res = c.run(rng=np.random.default_rng(1))
    assert st.nmode == 1
    assert "m" in res


def test_circuit_channel_chain_loss_amp_pn():
    c = (
        GaussianCircuit(1)
        .squeeze(0, r=0.5)
        .loss(0, T=0.8)
        .amplifier(0, G=1.5)
        .phase_noise(0, sigma=0.2)
    )
    st = c.run()
    direct = squeeze(GaussianState.vacuum(1), 0.5)
    direct = loss(direct, 0.8, mode=0)
    direct = amplifier(direct, 1.5, mode=0)
    direct = phase_noise(direct, 0.2, mode=0)
    np.testing.assert_allclose(st.V, direct.V, atol=1e-12)
    assert mean_photon(st) >= 0
    assert st.is_physical()


def test_circuit_repr_shows_channel_ops():
    c = GaussianCircuit(1)
    c.amplifier(0, G=2.0)
    c.phase_noise(0, sigma=0.1)
    c.gaussian_channel(np.eye(2), np.zeros((2, 2)), validate=False)
    s = repr(c)
    assert "amplifier" in s
    assert "phase_noise" in s
    assert "gaussian_channel" in s
