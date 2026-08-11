"""F2 measures: PNR (sample/condition) + heterodyne (sample/condition)
— vision §4 F2, coherent POVM |β⟩⟨β|/π, Born-rule conditioning."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.fock import FockDensity, FockState
from cvsim.fock.gates import two_mode_squeeze
from cvsim.fock.observables import (
    heterodyne_condition,
    heterodyne_sample,
    heterodyne_sample_and_condition,
    pnr_condition,
    pnr_sample,
    pnr_sample_and_condition,
    pnrd_probs,
)

# -- PNR --------------------------------------------------------------------


def test_pnr_sample_statistics() -> None:
    rng = np.random.default_rng(42)
    st = FockState.coherent(20, 1.2)
    n = np.array([pnr_sample(st, rng=rng) for _ in range(2000)])
    p = pnrd_probs(st)
    emp = np.bincount(n, minlength=p.size) / n.size
    np.testing.assert_allclose(emp[:8], p[:8], atol=3e-2)


def test_pnr_condition_1mode_pure_projective() -> None:
    st = FockState.coherent(12, 0.9)
    out = pnr_condition(st, 0, 3)
    np.testing.assert_allclose(out.amps, FockState.fock(3, 12).amps, atol=1e-14)


def test_pnr_condition_1mode_zero_probability() -> None:
    st = FockState.fock(2, 8)
    with pytest.raises(ValueError):
        pnr_condition(st, 0, 5)
    with pytest.raises(IndexError):
        pnr_condition(st, 0, 99)


def test_pnr_condition_2mode_pure() -> None:
    # |1,2⟩ + |0,3⟩ superposition: condition n=1 on mode 0 → |2⟩
    amps = np.zeros((8, 8), dtype=complex)
    amps[1, 2] = 0.6
    amps[0, 3] = 0.8
    st = FockState(amps=amps)
    out = pnr_condition(st, 0, 1)
    np.testing.assert_allclose(out.amps, FockState.fock(2, 8).amps, atol=1e-14)
    out2 = pnr_condition(st, 1, 3)
    # ⟨3| on mode1: ψ[0,3]*|0⟩ + ψ[1,3]... wait |1,2⟩ has mode1=2 → only |0⟩ component
    np.testing.assert_allclose(out2.amps, FockState.fock(0, 8).amps, atol=1e-14)


def test_pnr_condition_2mode_density() -> None:
    st = FockState.fock2(1, 0, 6)
    d = FockDensity.from_pure(st)
    out = pnr_condition(d, 0, 1)
    np.testing.assert_allclose(out.rho, FockDensity.from_pure(FockState.fock2(1, 0, 6)).rho, atol=1e-14)


def test_pnr_sample_and_condition_roundtrip() -> None:
    rng = np.random.default_rng(7)
    st = FockState.coherent(15, 0.5)
    n, out = pnr_sample_and_condition(st, rng=rng)
    assert 0 <= n < 15
    assert abs(np.sum(abs(out.amps) ** 2) - 1.0) < 1e-12


# -- heterodyne -------------------------------------------------------------


def test_heterodyne_condition_1mode_pure_coherent() -> None:
    st = FockState.squeezed(12, 0.4)
    beta = 0.8 + 0.3j
    out = heterodyne_condition(st, 0, beta)
    ref = FockState.coherent(12, beta)
    np.testing.assert_allclose(out.amps, ref.amps, atol=1e-14)


def test_heterodyne_condition_2mode_pure() -> None:
    # |1⟩₀|2⟩₁: condition β on mode 1 → ⟨β|2⟩·|1⟩ ∝ |1⟩
    st = FockState.fock2(1, 2, 10)
    out = heterodyne_condition(st, 1, 1.0)
    np.testing.assert_allclose(out.amps, FockState.fock(1, 10).amps, atol=1e-14)
    # mode 0: ⟨β|1⟩·|2⟩ ∝ |2⟩ (global phase allowed)
    out0 = heterodyne_condition(st, 0, 0.5j)
    assert abs(np.vdot(out0.amps, FockState.fock(2, 10).amps)) > 1.0 - 1e-14


def test_heterodyne_condition_2mode_density() -> None:
    d = FockDensity.from_pure(FockState.fock2(0, 3, 8))
    out = heterodyne_condition(d, 1, 0.7)
    np.testing.assert_allclose(out.rho, out.rho.conj().T, atol=1e-14)
    np.testing.assert_allclose(np.trace(out.rho), 1.0, atol=1e-12)


def test_heterodyne_sample_statistics_vacuum() -> None:
    """Q(β) for vacuum = e^{−|β|²}/π — sample |β|² ~ Exp(1)."""
    rng = np.random.default_rng(3)
    st = FockState.vacuum(12)
    bs = np.array([heterodyne_sample(st, rng=rng) for _ in range(800)])
    r2 = np.abs(bs) ** 2
    np.testing.assert_allclose(r2.mean(), 1.0, atol=0.15)


def test_heterodyne_sample_statistics_coherent() -> None:
    """Q(β) of |α⟩ = e^{−|β−α|²}/π — mean β ≈ α."""
    rng = np.random.default_rng(11)
    alpha = 1.0 + 0.0j
    st = FockState.coherent(20, alpha)
    bs = np.array([heterodyne_sample(st, rng=rng, lim=6.0) for _ in range(800)])
    np.testing.assert_allclose(bs.real.mean(), alpha.real, atol=0.12)
    np.testing.assert_allclose(bs.imag.mean(), 0.0, atol=0.12)


def test_heterodyne_sample_and_condition_roundtrip() -> None:
    rng = np.random.default_rng(5)
    st = FockState.cat(16, 1.0, even=True)
    b, out = heterodyne_sample_and_condition(st, rng=rng)
    assert isinstance(b, complex)
    assert abs(np.sum(abs(out.amps) ** 2) - 1.0) < 1e-12


def test_heterodyne_condition_probability() -> None:
    """p(β) = ⟨β|ρ|β⟩/π: Born weight of the conditioned state."""
    st = FockState.fock2(0, 2, 10)
    # Q(β) on mode1 marginal |2⟩: e^{−|β|²}|β|⁴/2
    beta = 0.9
    from cvsim.fock.observables import _q_function

    q = _q_function(st, 1, np.array([beta]))[0]
    expected = np.exp(-abs(beta) ** 2) * abs(beta) ** 4 / 2.0
    np.testing.assert_allclose(q, expected, atol=1e-12)


def test_heterodyne_matches_tms_marginal() -> None:
    """TMS marginal is thermal: Q(β) = e^{−|β|²/(n̄+1)}/(π(n̄+1))."""
    r = 0.4
    st = two_mode_squeeze(FockState.vacuum(16, nmode=2), r)
    nbar = np.sinh(r) ** 2
    from cvsim.fock.observables import _q_function

    betas = np.array([0.3, 0.8 + 0.2j, 1.1j])
    q = _q_function(st, 0, betas)
    expected = np.exp(-np.abs(betas) ** 2 / (nbar + 1.0)) / (nbar + 1.0)
    np.testing.assert_allclose(q, expected, atol=1e-6)
