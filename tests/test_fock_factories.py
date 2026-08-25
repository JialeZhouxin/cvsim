"""F1 factories + truncation engineering: coherent/squeezed/cat/thermal
+ leakage trio (vision-fock-simulator §4 F1 + §5, ADR-0004)."""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.special import gammainc

from cvsim.fock import (
    FockDensity,
    FockState,
    check_leakage,
    estimate_leakage,
    truncation_leakage,
)
from cvsim.fock.observables import homodyne_var

# -- coherent --------------------------------------------------------------


def test_coherent_coefficients_ratio() -> None:
    alpha = 1.2 + 0.3j
    st = FockState.coherent(12, alpha)
    n = np.arange(12)
    expected_ratio = (alpha**n / np.sqrt(np.array([math.factorial(k) for k in n]))).astype(complex)
    # c_n = c_0 * α^n/√(n!);  ratio c_n/c_0 must match
    ratios = st.amps / st.amps[0]
    np.testing.assert_allclose(ratios, expected_ratio / expected_ratio[0], atol=1e-12)


def test_coherent_renormalized() -> None:
    st = FockState.coherent(8, 2.0)
    np.testing.assert_allclose(np.sum(abs(st.amps) ** 2), 1.0, atol=1e-14)


def test_coherent_tail_analytic() -> None:
    alpha = 2.0
    for cutoff in (5, 8, 15):
        st = FockState.coherent(cutoff, alpha)
        np.testing.assert_allclose(st.tail, gammainc(cutoff, abs(alpha) ** 2), atol=1e-14)
    # large alpha + large cutoff: tail small, no underflow (regularized gamma)
    st = FockState.coherent(2750, 50.0)
    assert 0.0 < st.tail < 1e-5


def test_coherent_estimate_matches_tail() -> None:
    alpha = 1.5
    st = FockState.coherent(6, alpha)
    est = estimate_leakage(st, 30)
    np.testing.assert_allclose(est, st.tail, atol=1e-12)


# -- squeezed --------------------------------------------------------------


def test_squeezed_zero_is_vacuum() -> None:
    st = FockState.squeezed(10, 0.0)
    np.testing.assert_allclose(st.amps, FockState.vacuum(10).amps, atol=1e-14)
    assert st.tail == 0.0


def test_squeezed_hand_coefficients() -> None:
    r = 0.5
    st = FockState.squeezed(8, r)
    sech = 1.0 / np.cosh(r)
    renorm = np.sqrt(1.0 - st.tail)  # amps = exact / renorm (truncated space)
    c0 = np.sqrt(sech)
    c2 = np.sqrt(sech) * (-1.0) * np.sqrt(2.0) / 2.0 * np.tanh(r)
    np.testing.assert_allclose(st.amps[0] * renorm, c0, atol=1e-14)
    np.testing.assert_allclose(st.amps[2] * renorm, c2, atol=1e-14)
    np.testing.assert_allclose(st.amps[1], 0.0, atol=1e-14)
    np.testing.assert_allclose(st.amps[3], 0.0, atol=1e-14)
    # renormalized
    np.testing.assert_allclose(np.sum(abs(st.amps) ** 2), 1.0, atol=1e-14)


def test_squeezed_phi_phase() -> None:
    r, phi = 0.4, np.pi / 2
    st = FockState.squeezed(8, r, phi)
    st0 = FockState.squeezed(8, r)
    np.testing.assert_allclose(st.amps[2], st0.amps[2] * np.exp(1j * phi), atol=1e-12)


def test_squeezed_tail_increases_with_r() -> None:
    tails = [FockState.squeezed(8, r).tail for r in (0.3, 0.7, 1.2)]
    assert tails[0] < tails[1] < tails[2]


# -- cat -------------------------------------------------------------------


def test_cat_even_odd_orthogonal() -> None:
    e = FockState.cat(20, 1.5, even=True)
    o = FockState.cat(20, 1.5, even=False)
    np.testing.assert_allclose(np.vdot(e.amps, o.amps), 0.0, atol=1e-12)


def test_cat_small_alpha_tends_vacuum() -> None:
    e = FockState.cat(10, 0.05, even=True)
    np.testing.assert_allclose(e.amps[0], 1.0, atol=1e-5)
    np.testing.assert_allclose(e.amps[1], 0.0, atol=1e-14)  # odd vanish
    np.testing.assert_allclose(np.sum(abs(e.amps) ** 2), 1.0, atol=1e-14)


def test_cat_matches_closed_form() -> None:
    # c_n = (⟨n|α⟩ ± ⟨n|−α⟩)/√(2(1 ± e^{−2|α|²})) — closed form per coefficient
    alpha, N = 1.5, 20
    n = np.arange(N)
    en = (
        np.exp(-(abs(alpha) ** 2) / 2.0)
        * alpha**n
        / np.sqrt(np.array([math.factorial(k) for k in n]))
    )
    # ⟨n|−α⟩ = e^{−|α|²/2}(−α)^n/√n!
    em = (
        np.exp(-(abs(alpha) ** 2) / 2.0)
        * (-alpha) ** n
        / np.sqrt(np.array([math.factorial(k) for k in n]))
    )
    c = (en + em) / np.sqrt(2.0 * (1.0 + np.exp(-2.0 * alpha**2)))
    st = FockState.cat(N, alpha, even=True)
    np.testing.assert_allclose(st.amps * np.sqrt(1 - st.tail), c, atol=1e-12)


def test_cat_homodyne_anchor() -> None:
    # Phase 5 anchor: ⟨x̂²⟩_even = [(1+4α²)+o]/[2(1+o)], o=e^{-2α²}; α=1.5 → 4.9506
    alpha = 1.5
    o = np.exp(-2 * alpha**2)
    expected = ((1 + 4 * alpha**2) + o) / (2 * (1 + o))
    st = FockState.cat(40, alpha, even=True)
    np.testing.assert_allclose(homodyne_var(st, 0, 0.0), expected, atol=1e-9)


# -- thermal ---------------------------------------------------------------


def test_thermal_closed_form() -> None:
    nbar = 1.3
    d = FockDensity.thermal(10, nbar)
    n = np.arange(10)
    expected = nbar**n / (nbar + 1.0) ** (n + 1.0)
    np.testing.assert_allclose(np.diag(d.rho), expected, atol=1e-14)
    np.testing.assert_allclose(np.trace(d.rho), 1.0 - d.tail, atol=1e-14)


def test_thermal_tail_closed_form() -> None:
    nbar = 2.0
    for cutoff in (4, 8):
        d = FockDensity.thermal(cutoff, nbar)
        np.testing.assert_allclose(d.tail, (nbar / (nbar + 1.0)) ** cutoff, atol=1e-14)


def test_thermal_copy_keeps_tail() -> None:
    d = FockDensity.thermal(6, 0.7)
    assert d.copy().tail == d.tail


# -- leakage trio ----------------------------------------------------------


def test_leakage_unknown_for_bare_state() -> None:
    st = FockState(amps=np.ones(6) / np.sqrt(6))
    assert truncation_leakage(st) is None


def test_check_leakage_warns() -> None:
    st = FockState.squeezed(6, 1.5)  # tail ≈ 0.42
    with pytest.warns(RuntimeWarning):
        check_leakage(st, warn_threshold=1e-4, fail_threshold=0.5)


def test_check_leakage_strict_raises() -> None:
    st = FockState.squeezed(6, 1.5)
    with pytest.raises(ValueError):
        check_leakage(st, validate=True, warn_threshold=1e-4)


def test_check_leakage_unknown_skips() -> None:
    st = FockState(amps=np.ones(6) / np.sqrt(6))
    check_leakage(st)  # must not raise/warn
    check_leakage(st, validate=True)


def test_check_leakage_fail_threshold() -> None:
    st = FockState.squeezed(5, 1.2)
    with pytest.raises(ValueError):
        check_leakage(st, fail_threshold=1e-6)


def test_estimate_leakage_requires_factory() -> None:
    st = FockState(amps=np.ones(6) / np.sqrt(6))
    with pytest.raises(ValueError):
        estimate_leakage(st, 10)


def test_estimate_leakage_cutoff_guard() -> None:
    st = FockState.coherent(6, 1.0)
    with pytest.raises(ValueError):
        estimate_leakage(st, 6)
