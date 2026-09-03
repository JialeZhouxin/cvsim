"""B9 Bosonic PNR probabilities and sampling."""

from __future__ import annotations

import math

import numpy as np

from cvsim.bosonic import (
    BosonicState,
    Component,
    coherent,
    gkp0,
    pnr_probs,
    pnr_sample,
)
from cvsim.fock import FockState
from cvsim.fock.gates import displace as fock_displace
from cvsim.fock.observables import pnrd_probs
from cvsim.gaussian import GaussianState


def test_pnr_probs_coherent_poisson() -> None:
    alpha = 1.0
    cutoff = 4
    p = pnr_probs(coherent(alpha), cutoff=cutoff)
    expected = np.array(
        [np.exp(-alpha**2) * alpha ** (2 * n) / math.factorial(n) for n in range(cutoff)]
    )
    np.testing.assert_allclose(p, expected, atol=1e-10, rtol=1e-10)


def test_pnr_probs_vacuum_and_squeezed_even_structure() -> None:
    np.testing.assert_allclose(pnr_probs(BosonicState.vacuum(), cutoff=10)[1:], 0.0, atol=1e-10)
    r = 0.5
    p = pnr_probs(BosonicState.from_gaussian(GaussianState.squeezed(r)), cutoff=12)
    expected = np.zeros(12)
    expected[::2] = np.array(
        [
            1.0 / math.cosh(r)
            * math.factorial(2 * n)
            / (4.0**n * math.factorial(n) ** 2)
            * math.tanh(r) ** (2 * n)
            for n in range(6)
        ]
    )
    np.testing.assert_allclose(p, expected, atol=1e-9, rtol=1e-8)


def test_pnr_probs_non_diagonal_covariance_and_complex_displacement_matches_fock() -> None:
    gaussian = GaussianState.displaced_squeezed(0.9 + 0.4j, 0.5, 0.4)
    bosonic = BosonicState.from_gaussian(gaussian)
    fock = FockState.squeezed(70, 0.5, 0.8)
    fock = fock_displace(fock, 0.9 + 0.4j)
    np.testing.assert_allclose(pnr_probs(bosonic, cutoff=12), pnrd_probs(fock)[:12], atol=1e-8)


def test_pnr_probs_complex_weight_phase_cat_matches_fock() -> None:
    alpha = 0.8
    theta = 0.7
    overlap = np.exp(-2.0 * alpha**2)
    norm = 2.0 * (1.0 + overlap * np.cos(theta))
    r = np.sqrt(2.0) * alpha
    V = 0.5 * np.eye(2)
    components = [
        Component(V.copy(), np.array([r, 0.0]), 1.0 / norm),
        Component(V.copy(), np.array([-r, 0.0]), 1.0 / norm),
        Component(V.copy(), np.array([0.0, 1j * r]), overlap * np.exp(1j * theta) / norm),
        Component(V.copy(), np.array([0.0, -1j * r]), overlap * np.exp(-1j * theta) / norm),
    ]
    p = pnr_probs(BosonicState(components), cutoff=12)
    fock = FockState.coherent(70, alpha)
    minus = FockState.coherent(70, -alpha)
    amps = fock.amps + np.exp(1j * theta) * minus.amps
    amps /= np.linalg.norm(amps)
    np.testing.assert_allclose(p, np.abs(amps[:12]) ** 2, atol=1e-8)
    assert np.all(p >= 0.0)


def test_pnr_probs_gkp_full_finite_and_fock_crosscheck() -> None:
    state = gkp0(0.1, grid_size=2, cross="full", lattice="2d")
    p = pnr_probs(state, cutoff=20)
    assert p.dtype == np.float64
    assert p.shape == (20,)
    assert np.all(np.isfinite(p))
    assert np.all(p >= 0.0)
    # Rebuild finite comb from diagonal components as an independent Fock gold.
    fock = np.zeros(80, dtype=complex)
    squeeze_r = 0.5 * np.log(1.0 / 0.1)
    for component in state.components:
        if abs(component.rbar[1].imag) >= 1e-12:
            continue
        amp = FockState.squeezed(80, squeeze_r, 0.0)
        amp = fock_displace(amp, component.rbar[0].real / np.sqrt(2.0)).amps
        fock += np.sqrt(component.w.real) * amp
    fock /= np.linalg.norm(fock)
    np.testing.assert_allclose(p, np.abs(fock[:20]) ** 2, atol=2e-6)


def test_pnr_sample_seed_and_errors() -> None:
    state = coherent(1.0)
    first = pnr_sample(state, cutoff=12, rng=np.random.default_rng(0))
    second = pnr_sample(state, cutoff=12, rng=np.random.default_rng(0))
    assert first == second
    assert isinstance(first, int) and 0 <= first < 12
    for bad in (True, 0, -1, 1.5):
        try:
            pnr_probs(state, cutoff=bad)  # type: ignore[arg-type]
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted invalid cutoff {bad!r}")
