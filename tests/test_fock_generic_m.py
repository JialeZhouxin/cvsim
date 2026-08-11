"""F2 generic-m: FockState/FockDensity accept m=1..4 (dense ceiling, sparse F3)."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.fock import FockDensity, FockState


def test_fockstate_3mode_roundtrip() -> None:
    amps = np.zeros((4, 4, 4), dtype=complex)
    amps[1, 2, 3] = 1.0
    st = FockState(amps=amps)
    assert st.nmode == 3
    assert st.cutoff == 4
    d = FockDensity.from_pure(st)
    assert d.nmode == 3
    assert d.cutoff == 4
    assert d.rho.shape == (64, 64)
    # roundtrip: density of a basis state is |e⟩⟨e|
    e = np.zeros(64, dtype=complex)
    e[1 * 16 + 2 * 4 + 3] = 1.0
    np.testing.assert_allclose(d.rho, np.outer(e, e.conj()), atol=1e-14)


def test_fockstate_4mode_and_validation() -> None:
    st = FockState.vacuum(3, nmode=4)
    assert st.nmode == 4 and st.cutoff == 3
    with pytest.raises(ValueError):
        FockState(np.zeros((3, 3, 3, 3, 3), dtype=complex))  # m=5 above ceiling
    # per-mode cutoffs (F3): unequal axes are legal now
    st = FockState(np.zeros((4, 5), dtype=complex))
    assert st.nmode == 2 and st.cutoff == 4


def test_fockstate_vacuum_generic_m() -> None:
    for m in (1, 2, 3):
        v = FockState.vacuum(6, nmode=m)
        assert v.nmode == m
        assert abs(np.sum(abs(v.amps) ** 2) - 1.0) < 1e-12
    with pytest.raises(ValueError):
        FockState.vacuum(6, nmode=5)


def test_fockdensity_generic_m_validation() -> None:
    d = FockDensity(rho=np.eye(8, dtype=complex), nmode=3)  # 2³=8
    assert d.cutoff == 2
    with pytest.raises(ValueError):
        FockDensity(rho=np.eye(10, dtype=complex), nmode=3)  # not cutoff³
    with pytest.raises(ValueError):
        FockDensity(rho=np.eye(4, dtype=complex), nmode=5)
    assert FockDensity(rho=np.eye(4, dtype=complex), nmode=1).cutoff == 4  # any d valid
    with pytest.raises(ValueError):
        FockDensity(rho=np.eye(4, dtype=complex), nmode=0)


def test_partial_trace_m3_honest_boundary() -> None:
    from cvsim.fock.analyse import partial_trace

    st = FockState.vacuum(4, nmode=3)
    with pytest.raises(NotImplementedError):
        partial_trace(st, 0)


def test_2mode_regression_untouched() -> None:
    st = FockState.fock2(1, 2, 6)
    assert st.nmode == 2
    d = FockDensity.from_pure(st)
    assert d.nmode == 2 and d.cutoff == 6
    np.testing.assert_allclose(np.trace(d.rho), 1.0, atol=1e-12)
