"""F5 bridge cross-check suite — Gaussian analytic vs Fock numeric (Phase F5).

Vision §4 F5 exit 1–2: PNR / mean_photon / threshold agree atol 1e-7 between
the Gaussian analytic side (``cvsim.bridge`` elements + ``cvsim.gaussian``
observables) and Fock numerics (``cvsim.fock`` pnrd_probs / mean_photon /
loss Kraus), for coherent / squeezed / thermal states (small m).

Leakage discipline (vision §5 never-silent, ADR-0004): every comparison is
gated by ``_check_tail`` — an explicit truncation-tail assert (< 1e-9).
Badly truncated (or unknown-tail) states fail loudly instead of being
compared silently; see ``test_leakage_discipline_*``.

Cutoffs are chosen in the tail-rich regime (design 2026-08-12):
coherent cutoff=40 (tail gammainc(40, |α|²) ≪ 1e-9 for |α| ≤ 1.0);
squeezed r ≤ 0.4 cutoff=30 (tail < 1e-9, pure-leakage-driven 3.4e-8 at
r=0.5 cutoff=20 would violate the gate — r ≤ 0.4 keeps margin);
thermal (nbar, cutoff): (0.5, 30) / (1.0, 40) / (2.0, 60) (tail
(nbar/(nbar+1))^cutoff < 1e-9). The gates re-assert this in-code.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from cvsim import bridge
from cvsim.fock import FockDensity, FockState, loss, pnrd_probs
from cvsim.fock import mean_photon as fock_mean
from cvsim.gaussian import (
    GaussianState,
)
from cvsim.gaussian import (
    loss as gauss_loss,
)
from cvsim.gaussian import (
    mean_photon as gauss_mean,
)
from cvsim.gaussian import (
    p_click as gauss_p_click,
)

LEAK_ATOL = 1e-9


def _check_tail(tail: float | None, atol: float = LEAK_ATOL) -> None:
    """Never-silent truncation gate (vision §5): refuse to compare
    unknown or too-large tails. Every comparison below calls this first."""
    assert tail is not None, "truncation tail unknown — cannot compare silently"
    assert tail < atol, (
        f"truncation tail {tail:.3g} >= {atol:.0e} — cutoff too small, "
        "refuse to compare (leakage discipline)"
    )


# ---------------------------------------------------------------------------
# PNR distributions: pnrd_probs vs bridge analytic elements
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("alpha", [0.3, 0.8, 1.0, 0.5 + 0.3j])
def test_pnr_probs_coherent(alpha: complex) -> None:
    cutoff = 40  # tail = gammainc(40, |α|²) ≪ 1e-9 for |α| ≤ 1.0
    psi = FockState.coherent(cutoff, alpha)
    _check_tail(psi.tail)
    p = pnrd_probs(psi)
    for n in range(12):
        np.testing.assert_allclose(p[n], abs(bridge.coherent_element(n, alpha)) ** 2, atol=1e-7)


@pytest.mark.parametrize("r", [0.2, 0.3, 0.4])
def test_pnr_probs_squeezed(r: float) -> None:
    cutoff = 30  # r ≤ 0.4 → tail ≪ 1e-9 (r=0.5@20 gives 3.4e-8: rejected)
    psi = FockState.squeezed(cutoff, r)
    _check_tail(psi.tail)
    p = pnrd_probs(psi)
    for n in range(12):
        np.testing.assert_allclose(p[n], abs(bridge.squeezed_element(n, r)) ** 2, atol=1e-7)
    # odd photons vanish for squeezed vacuum (φ=0 convention)
    np.testing.assert_allclose(p[1::2][:6], 0.0, atol=1e-12)


@pytest.mark.parametrize("nbar,cutoff", [(0.5, 30), (1.0, 40), (2.0, 60)])
def test_pnr_probs_thermal(nbar: float, cutoff: int) -> None:
    rho = FockDensity.thermal(cutoff, nbar)
    _check_tail(rho.tail)
    p = pnrd_probs(rho)
    for n in range(12):
        np.testing.assert_allclose(p[n], bridge.thermal_diag(n, nbar), atol=1e-7)


# ---------------------------------------------------------------------------
# mean_photon: Gaussian analytic / closed form vs Fock numeric
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("alpha", [0.3, 0.8, 1.0, 0.5 + 0.3j])
def test_mean_photon_coherent(alpha: complex) -> None:
    st = GaussianState.coherent(alpha)
    # Gaussian analytic ½(⟨x²⟩+⟨p²⟩−1) vs closed form |α|²
    np.testing.assert_allclose(gauss_mean(st), abs(alpha) ** 2, atol=1e-12)
    psi = FockState.coherent(40, alpha)
    _check_tail(psi.tail)
    np.testing.assert_allclose(fock_mean(psi), abs(alpha) ** 2, atol=1e-7)


@pytest.mark.parametrize("r", [0.2, 0.4])
def test_mean_photon_squeezed(r: float) -> None:
    st = GaussianState.squeezed(r)
    np.testing.assert_allclose(gauss_mean(st), math.sinh(r) ** 2, atol=1e-12)
    psi = FockState.squeezed(30, r)
    _check_tail(psi.tail)
    np.testing.assert_allclose(fock_mean(psi), math.sinh(r) ** 2, atol=1e-7)


@pytest.mark.parametrize("nbar,cutoff", [(0.5, 30), (2.0, 60)])
def test_mean_photon_thermal(nbar: float, cutoff: int) -> None:
    st = GaussianState.thermal(nbar)
    np.testing.assert_allclose(gauss_mean(st), nbar, atol=1e-12)
    rho = FockDensity.thermal(cutoff, nbar)
    _check_tail(rho.tail)
    np.testing.assert_allclose(fock_mean(rho), nbar, atol=1e-7)


# ---------------------------------------------------------------------------
# Threshold: Gaussian p_click (= 1 − bridge.vacuum_probability) vs Fock
# 1 − pnrd_probs[0]
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("alpha", [0.3, 0.8, 1.0])
def test_threshold_coherent(alpha: complex) -> None:
    st = GaussianState.coherent(alpha)
    got = gauss_p_click(st)
    np.testing.assert_allclose(got, 1.0 - math.exp(-(abs(alpha) ** 2)), atol=1e-12)
    psi = FockState.coherent(40, alpha)
    _check_tail(psi.tail)
    np.testing.assert_allclose(got, 1.0 - pnrd_probs(psi)[0], atol=1e-7)


def test_threshold_squeezed() -> None:
    for r in (0.2, 0.4):
        st = GaussianState.squeezed(r)
        got = gauss_p_click(st)
        # p0 = 1/√det(V+½I) = sech r (bridge.vacuum_probability analytic)
        np.testing.assert_allclose(got, 1.0 - 1.0 / math.cosh(r), atol=1e-12)
        psi = FockState.squeezed(30, r)
        _check_tail(psi.tail)
        np.testing.assert_allclose(got, 1.0 - pnrd_probs(psi)[0], atol=1e-7)


def test_threshold_thermal() -> None:
    for nbar, cutoff in ((0.5, 30), (2.0, 60)):
        st = GaussianState.thermal(nbar)
        got = gauss_p_click(st)
        np.testing.assert_allclose(got, 1.0 - 1.0 / (nbar + 1.0), atol=1e-12)
        rho = FockDensity.thermal(cutoff, nbar)
        _check_tail(rho.tail)
        np.testing.assert_allclose(got, 1.0 - pnrd_probs(rho)[0], atol=1e-7)


# ---------------------------------------------------------------------------
# Lossy coherent chain: η sweep — Gaussian closed forms vs Fock loss Kraus
# ---------------------------------------------------------------------------

ALPHA_SWEEP = 0.8
CUTOFF_SWEEP = 40  # input tail gammainc(40, 0.64) ≈ 1e-18; loss moves mass
#                   down, so output tail ≤ input tail (bound used below)


@pytest.mark.parametrize("eta", [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
def test_lossy_coherent_eta_sweep(eta: float) -> None:
    alpha = ALPHA_SWEEP
    # leakage gate: the loss-channel output has no analytic tail (FockDensity
    # from Kraus, tail=None) — bound it by the input state's tail.
    psi_in = FockState.coherent(CUTOFF_SWEEP, alpha)
    _check_tail(psi_in.tail)

    rho = loss(psi_in, eta)  # Fock loss Kraus
    np.testing.assert_allclose(fock_mean(rho), eta * abs(alpha) ** 2, atol=1e-7)
    np.testing.assert_allclose(
        1.0 - pnrd_probs(rho)[0], 1.0 - math.exp(-eta * abs(alpha) ** 2), atol=1e-7
    )

    # same chain on the Gaussian side (channel numeric vs closed form)
    st = GaussianState.coherent(alpha)
    st_l = gauss_loss(st, eta)
    np.testing.assert_allclose(gauss_mean(st_l), eta * abs(alpha) ** 2, atol=1e-12)
    np.testing.assert_allclose(
        gauss_p_click(st_l), 1.0 - math.exp(-eta * abs(alpha) ** 2), atol=1e-12
    )


# ---------------------------------------------------------------------------
# Leakage discipline: the never-silent gate itself (negative tests)
# ---------------------------------------------------------------------------


def test_leakage_discipline_refuses_bad_truncation() -> None:
    # coherent cutoff=6, |α|=2.0: tail ≈ 0.21 ≫ 1e-9 — the gate must trip
    psi = FockState.coherent(6, 2.0)
    assert psi.tail is not None and psi.tail > 1e-9
    with pytest.raises(AssertionError, match="refuse to compare"):
        _check_tail(psi.tail)


def test_leakage_discipline_comparison_fails_without_guard() -> None:
    # without the tail gate, a naive atol=1e-7 comparison of the badly
    # truncated state must itself fail (renormalized p0 ≈ 0.0233 vs e^{-4})
    psi = FockState.coherent(6, 2.0)
    with pytest.raises(AssertionError):
        np.testing.assert_allclose(
            pnrd_probs(psi)[0], abs(bridge.coherent_element(0, 2.0)) ** 2, atol=1e-7
        )


def test_leakage_discipline_unknown_tail_rejected() -> None:
    # non-factory state: tail is None — never guessed, gate refuses
    psi = FockState(amps=np.array([1.0, 0.0], dtype=complex))
    assert psi.tail is None
    with pytest.raises(AssertionError, match="unknown"):
        _check_tail(psi.tail)


def test_leakage_discipline_squeezed_r050_at_cutoff20_rejected() -> None:
    # the measured 3.4e-8 tail (r=0.5, cutoff=20) must NOT pass the gate —
    # that is why the suite runs squeezed at r ≤ 0.4 / cutoff 30
    psi = FockState.squeezed(20, 0.5)
    assert psi.tail is not None and psi.tail > 1e-9
    with pytest.raises(AssertionError):
        _check_tail(psi.tail)
