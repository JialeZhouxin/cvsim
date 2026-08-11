"""F3 circuit: FockCircuit DSL — builder, compile/run parity, measure, channels."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.fock import FockDensity, FockState
from cvsim.fock.circuit import FockCircuit, ParamRef
from cvsim.fock.gates import (
    beamsplitter,
    cz,
    displace,
    kerr,
    phase,
    squeeze,
    two_mode_squeeze,
)
from cvsim.fock.observables import pnr_condition


def test_single_gate_matches_direct() -> None:
    c = FockCircuit(1, cutoff=12)
    c.squeeze(0, r=0.4)
    c.phase(0, theta=0.3)
    c.displace(0, alpha=0.5 + 0.2j)
    c.kerr(0, chi=0.1)
    out = c.run()
    ref = kerr(
        displace(phase(squeeze(FockState.vacuum(12), 0.4), 0.3), 0.5 + 0.2j),
        0.1,
    )
    np.testing.assert_allclose(out.amps, ref.amps, atol=1e-12)


def test_twomode_merged_matches_direct() -> None:
    c = FockCircuit(2, cutoff=10)
    c.squeeze(0, r=0.3)
    c.beamsplitter(0, 1, theta=0.7, phi=0.2)
    c.two_mode_squeeze(0, 1, r=0.25)
    c.cz(0, 1, weight=0.8)
    out = c.run()
    ref = cz(
        two_mode_squeeze(
            beamsplitter(squeeze(FockState.vacuum(10, nmode=2), 0.3), 0.7, 0.2),
            0.25,
        ),
        0.8,
    )
    np.testing.assert_allclose(out.amps, ref.amps, atol=1e-10)


def test_symbolic_params_and_feedforward() -> None:
    c = FockCircuit(2, cutoff=12)
    c.squeeze(1, r='r_s')
    c.measure_pnr(1, name='m_n')
    c.displace(0, alpha=ParamRef('m_n', gain=0.2))
    rng = np.random.default_rng(9)
    st, results = c.run(r_s=0.6, rng=rng)
    assert 'm_n' in results and isinstance(results['m_n'], int)
    assert 0 <= results['m_n'] < 12
    # deterministic with same rng
    rng2 = np.random.default_rng(9)
    st2, res2 = c.run(r_s=0.6, rng=rng2)
    assert results == res2
    np.testing.assert_allclose(st.amps, st2.amps, atol=1e-14)


def test_compile_run_parity() -> None:
    c = FockCircuit(2, cutoff=8)
    c.beamsplitter(0, 1)
    c.phase(0, theta=0.4)
    c.measure_pnr(0, name='n0')
    c.displace(1, alpha=ParamRef('n0', gain=0.1))
    rng = np.random.default_rng(3)
    st1, r1 = c.run(rng=rng)
    rng2 = np.random.default_rng(3)
    st2, r2 = c.compile().run(rng=rng2)
    assert r1 == r2
    np.testing.assert_allclose(st1.amps, st2.amps, atol=1e-14)


def test_measure_pnr_conditioning() -> None:
    c = FockCircuit(2, cutoff=10)
    c.squeeze(0, r=0.5)
    c.measure_pnr(1, name='n1')  # vacuum mode → n=0 almost surely
    st, results = c.run(rng=np.random.default_rng(1))
    assert results['n1'] == 0
    ref = pnr_condition(squeeze(FockState.vacuum(10, nmode=2), 0.5), 1, 0)
    np.testing.assert_allclose(st.amps, ref.amps, atol=1e-12)


def test_channel_breaks_segment_and_density_path() -> None:
    """loss → density; gates after loss run the UρU† Kronecker path."""
    c = FockCircuit(1, cutoff=8)
    c.squeeze(0, r=0.4)
    c.loss(0, eta=0.7)
    c.phase(0, theta=0.5)  # after channel: density path
    out = c.run()
    assert isinstance(out, FockDensity)
    ref = phase(FockDensity.from_pure(squeeze(FockState.vacuum(8), 0.4)), 0.5)
    from cvsim.fock.channels import loss as ch_loss

    ref = phase(ch_loss(FockDensity.from_pure(squeeze(FockState.vacuum(8), 0.4)), 0.7), 0.5)
    np.testing.assert_allclose(out.rho, ref.rho, atol=1e-12)


def test_density_2mode_channel_path() -> None:
    c = FockCircuit(2, cutoff=6)
    c.two_mode_squeeze(0, 1, r=0.3)
    c.loss(0, eta=0.6)
    c.beamsplitter(0, 1, theta=0.5)  # 2-mode density Kronecker
    out = c.run()
    assert isinstance(out, FockDensity)
    assert out.nmode == 2
    np.testing.assert_allclose(np.trace(out.rho), 1.0, atol=1e-10)


def test_per_mode_cutoffs() -> None:
    c = FockCircuit(2, cutoff=[6, 10])
    c.squeeze(0, r=0.3)
    c.phase(1, theta=0.2)
    out = c.run()
    assert out.amps.shape == (6, 10)
    with pytest.raises(ValueError):
        c2 = FockCircuit(2, cutoff=[6, 10])
        c2.beamsplitter(0, 1)  # unequal cutoffs on a two-mode gate
        c2.run()


def test_apply_unitary_circuit() -> None:
    # truncated-space swap on (N²,N²) — gates.apply_unitary convention
    N = 8
    perm = np.zeros((N * N, N * N), dtype=complex)
    for n0 in range(N):
        for n1 in range(N):
            perm[n1 * N + n0, n0 * N + n1] = 1.0
    c = FockCircuit(2, cutoff=N)
    c.squeeze(0, r=0.4)
    c.apply_unitary(perm, modes=[0, 1])
    out = c.run()
    ref = squeeze(FockState.vacuum(N, nmode=2), 0.4).amps.T  # swap = axis transpose
    np.testing.assert_allclose(out.amps, ref, atol=1e-12)


def test_interferometer_circuit() -> None:
    U = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
    c = FockCircuit(2, cutoff=8)
    c.squeeze(1, r=0.4)
    c.interferometer(U)
    out = c.run()
    ref = squeeze(FockState.vacuum(8, nmode=2), 0.4, mode=1).amps.T
    np.testing.assert_allclose(out.amps, ref, atol=1e-10)


def test_add_and_repr() -> None:
    c1 = FockCircuit(2, cutoff=8)
    c1.squeeze(0, r=0.3)
    c2 = FockCircuit(2, cutoff=8)
    c2.phase(1, theta=0.2)
    c3 = c1 + c2
    assert len(c3) == 2
    out = c3.run()
    np.testing.assert_allclose(out.amps, phase(squeeze(FockState.vacuum(8, nmode=2), 0.3), 0.2, mode=1).amps, atol=1e-12)
    assert "FockCircuit(2, cutoff=[8, 8])" in repr(c3)
    with pytest.raises(ValueError):
        c1 += FockCircuit(2, cutoff=10)
