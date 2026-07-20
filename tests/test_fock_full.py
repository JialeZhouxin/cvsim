"""Fock full loop: Kerr + BS + PNRD (1–2 mode)."""

from __future__ import annotations

import numpy as np

from cvsim.fock import (
    FockState,
    beamsplitter,
    kerr,
    mean_photon,
    norm,
    pnrd_probs,
)


def test_kerr_phase_on_fock():
    chi = 0.3
    st = FockState.fock(3, 12)
    st2 = kerr(st, chi)
    # relative to n=0 global: amp[3] gains e^{i chi * 9}
    expect = np.exp(1j * chi * 9)
    assert abs(st2.amps[3] - expect) < 1e-12
    assert abs(abs(st2.amps[3]) - 1.0) < 1e-12


def test_bs_vacuum_stays_vacuum():
    st = beamsplitter(FockState.vacuum(8, nmode=2), np.pi / 4)
    assert abs(abs(st.amps[0, 0]) - 1.0) < 1e-10
    assert abs(norm(st) - 1.0) < 1e-10
    rest = np.linalg.norm(st.amps) ** 2 - abs(st.amps[0, 0]) ** 2
    assert rest < 1e-12


def test_bs_single_photon_5050():
    # |1,0⟩ → BS(π/4) ≈ (|10⟩ + |01⟩)/√2
    st = beamsplitter(FockState.fock2(1, 0, 12), np.pi / 4)
    p10 = abs(st.amps[1, 0]) ** 2
    p01 = abs(st.amps[0, 1]) ** 2
    assert abs(p10 - 0.5) < 1e-6
    assert abs(p01 - 0.5) < 1e-6
    assert abs(norm(st) - 1.0) < 1e-10


def test_pnrd_sums_to_norm():
    st1 = FockState.fock(2, 10)
    p1 = pnrd_probs(st1)
    assert abs(p1.sum() - norm(st1)) < 1e-14
    st2 = beamsplitter(FockState.fock2(1, 0, 10), 0.3)
    p2 = pnrd_probs(st2)
    assert abs(p2.sum() - norm(st2)) < 1e-12
    m0 = pnrd_probs(st2, mode=0)
    assert abs(m0.sum() - norm(st2)) < 1e-12


def test_two_mode_mean_photon():
    st = FockState.fock2(2, 1, 8)
    assert abs(mean_photon(st, 0) - 2.0) < 1e-15
    assert abs(mean_photon(st, 1) - 1.0) < 1e-15
    assert abs(mean_photon(st) - 3.0) < 1e-15
