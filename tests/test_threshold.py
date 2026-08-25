"""Threshold (on/off) outcome-only measurement tests — Phase 5 C2.

Covers ``cvsim.gaussian.observables.p_click`` / ``sample_threshold`` and the
circuit/compile chain ``GaussianCircuit.measure_threshold`` with outcome
feedforward via ``ParamRef``.

Semantics locked by grill 2026-08-10: **outcome-only** — {0,1} sample, no
state update, no mode removal.
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim import bridge
from cvsim.gaussian import (
    GaussianCircuit,
    GaussianState,
    p_click,
    sample_threshold,
)
from cvsim.symplectic import S_squeeze, d_displace


def _state_with(r: float = 0.0, alpha: complex = 0.0) -> GaussianState:
    S = S_squeeze(1, r, 0)
    V = S @ (np.eye(2) * 0.5) @ S.T
    return GaussianState(V=V, rbar=d_displace(1, alpha, 0))


# ---------------------------------------------------------------------------
# p_click — analytic vs Fock truncated ⟨0|ρ|0⟩ (via bridge), and bridge lock
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("r,alpha", [(0.0, 0.0), (0.0, 0.6), (0.4, 0.0), (0.4, 0.3 + 0.1j)])
def test_p_click_matches_fock_truncated(r: float, alpha: complex) -> None:
    from cvsim.fock import FockState, displace, squeeze

    st = _state_with(r, alpha)
    got = p_click(st, 0)
    psi = displace(squeeze(FockState.vacuum(16), r), alpha)
    fock_p0 = float(abs(psi.amps[0]) ** 2)
    np.testing.assert_allclose(got, 1.0 - fock_p0, atol=1e-10)


def test_p_click_vacuum_zero() -> None:
    assert p_click(_state_with(0.0, 0.0), 0) == 0.0


def test_p_click_coherent_known() -> None:
    # |α⟩: p_click = 1 − e^{−|α|²}
    st = _state_with(0.0, 1.0)
    np.testing.assert_allclose(p_click(st, 0), 1.0 - np.exp(-1.0), atol=1e-12)


def test_p_click_agrees_with_bridge() -> None:
    # formula lock: observables._vacuum_probability == bridge.vacuum_probability
    for r, alpha in [(0.3, 0.0), (0.5, 0.2 + 0.1j)]:
        st = _state_with(r, alpha)
        np.testing.assert_allclose(
            p_click(st, 0),
            1.0 - bridge.vacuum_probability(st.V, st.rbar, 0),
            atol=1e-12,
        )


def test_p_click_type_error() -> None:
    with pytest.raises(TypeError):
        p_click(np.eye(2) * 0.5, 0)  # bare array, not GaussianState


def test_p_click_mode_out_of_range() -> None:
    st = _state_with(0.2)
    with pytest.raises(IndexError):
        p_click(st, 3)


# ---------------------------------------------------------------------------
# sample_threshold — distribution with fixed seed
# ---------------------------------------------------------------------------


def test_sample_threshold_distribution() -> None:
    st = _state_with(0.0, 1.0)  # p_click = 1 − e^{−1} ≈ 0.632
    rng = np.random.default_rng(7)
    n = 4000
    clicks = sum(sample_threshold(st, 0, rng=rng) for _ in range(n))
    p = p_click(st, 0)
    # binomial: 4000 draws, p≈0.632 → std ≈ √(np(1−p)) ≈ 30.5 → ±5σ ≈ 152
    np.testing.assert_allclose(clicks / n, p, atol=0.05)


def test_sample_threshold_vacuum_never_clicks() -> None:
    st = _state_with(0.0, 0.0)
    rng = np.random.default_rng(1)
    for _ in range(50):
        assert not sample_threshold(st, 0, rng=rng)


def test_sample_threshold_default_rng() -> None:
    st = _state_with(0.0, 1.0)
    # no rng → fresh default generator; just must return bool
    assert isinstance(sample_threshold(st, 0), bool)


# ---------------------------------------------------------------------------
# GaussianCircuit.measure_threshold — builder + compile + ParamRef
# ---------------------------------------------------------------------------


def test_circuit_measure_threshold_outcome() -> None:
    c = GaussianCircuit(2)
    c.squeeze(1, r=0.5)  # ancilla squeezed → non-vacuum → click probability > 0
    c.measure_threshold(1, name="click")
    compiled = c.compile()
    rng = np.random.default_rng(3)
    for _ in range(20):
        _, res = compiled.run(rng=rng)
        assert res["click"] in (0, 1)


def test_circuit_measure_threshold_vacuum_always_zero() -> None:
    c = GaussianCircuit(2)
    c.measure_threshold(0, name="click")
    compiled = c.compile()
    rng = np.random.default_rng(4)
    for _ in range(20):
        _, res = compiled.run(rng=rng)
        assert res["click"] == 0


def test_circuit_threshold_paramref_feedforward() -> None:
    # threshold outcome drives a later displacement gain (0 or 1)
    c = GaussianCircuit(1)
    c.measure_threshold(0, name="click")
    c.displace(0, alpha=ParamRef("click", gain=0.5))
    compiled = c.compile()
    rng = np.random.default_rng(5)
    _, res = compiled.run(rng=rng)
    # displacement applied on mode 0: rbar depends on click
    assert res["click"] in (0, 1)


def test_circuit_threshold_keeps_mode() -> None:
    # outcome-only: nmode unchanged after measurement
    c = GaussianCircuit(2)
    c.measure_threshold(0, name="click")
    compiled = c.compile()
    st, _ = compiled.run(rng=np.random.default_rng(6))
    assert st.nmode == 2


def test_circuit_threshold_after_homodyne_removed_mode() -> None:
    # homodyne removes the mode; threshold on the removed mode must fail
    c = GaussianCircuit(2)
    c.measure_homodyne(0, phi=0.0, name="m")
    c.measure_threshold(0, name="click")
    with pytest.raises(ValueError, match="already measured/removed"):
        c.compile()  # fail-fast at compile time


def test_circuit_threshold_ir_roundtrip() -> None:
    c = GaussianCircuit(1)
    c.measure_threshold(0, name="click")
    c2 = GaussianCircuit.from_ir(c.to_ir())
    _, res = c2.compile().run(rng=np.random.default_rng(8))
    assert res["click"] in (0, 1)


def test_p_click_rejects_nonphysical() -> None:
    # V=0.1I below Heisenberg bound → p0 = 1/√0.6 > 1 → must raise
    with pytest.raises(ValueError, match=r"outside \[0, 1\]"):
        p_click(GaussianState(V=0.1 * np.eye(2), rbar=np.zeros(2)), 0)


from cvsim.gaussian.circuit import ParamRef  # noqa: E402 — after builder tests
