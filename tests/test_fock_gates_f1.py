"""F1 gates: cz/cx/mach_zehnder/interferometer/apply_unitary (continuous-
variable physics, matches Gaussian conventions — vision-fock-simulator §4 F1)."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.fock import FockDensity, FockState
from cvsim.fock.gates import (
    apply_unitary,
    beamsplitter,
    cx,
    cz,
    interferometer,
    mach_zehnder,
    phase,
    squeeze,
)

# -- helpers ---------------------------------------------------------------


def _is_unitary(U: np.ndarray, atol: float = 1e-10) -> bool:
    return bool(np.allclose(U @ U.conj().T, np.eye(U.shape[0]), atol=atol))


# -- cz --------------------------------------------------------------------


def test_cz_zero_weight_identity() -> None:
    st0 = FockState.fock2(1, 1, 12)
    np.testing.assert_allclose(cz(st0, 0.0).amps, st0.amps, atol=1e-14)


def test_cz_unitary() -> None:
    for st0 in (FockState.fock2(2, 0, 10), FockState.fock2(1, 1, 10)):
        out = cz(st0, 0.7)
        np.testing.assert_allclose(
            np.sum(abs(out.amps) ** 2), np.sum(abs(st0.amps) ** 2), atol=1e-12
        )


def test_cz_requires_two_modes() -> None:
    with pytest.raises(ValueError):
        cz(FockState.vacuum(8), 0.5)


def _gauss_mean_photon(gst: object, mode: int) -> float:
    """⟨n_m⟩ = ½(tr V_sub − 1) from the Gaussian V (xxpp, ħ=1)."""
    V = gst.V  # type: ignore[attr-defined]
    nm = V.shape[0] // 2  # xxpp block order: [x0..x_{m-1}, p0..p_{m-1}]
    idx = [mode, mode + nm]
    sub = V[np.ix_(idx, idx)]
    return float(0.5 * (np.trace(sub) - 1.0))


def test_cz_against_gaussian() -> None:
    """CZ on squeezed×vacuum matches Gaussian cz (same physics, xxpp ħ=1)."""
    from cvsim.fock.observables import mean_photon as f_mean
    from cvsim.gaussian import GaussianState
    from cvsim.gaussian import cz as g_cz

    r, g = 0.6, 0.5
    N = 24
    fst = squeeze(FockState.vacuum(N, nmode=2), r, 0)
    fst = cz(fst, g, 0, 1)
    gst = GaussianState.squeezed(r, nmode=2, mode=0)
    gst = g_cz(gst, g, 0, 1)
    for m in (0, 1):
        np.testing.assert_allclose(
            f_mean(fst, m), _gauss_mean_photon(gst, m), rtol=1e-4, atol=1e-5
        )


# -- cx --------------------------------------------------------------------


def test_cx_zero_weight_identity() -> None:
    st0 = FockState.fock2(1, 2, 10)
    np.testing.assert_allclose(cx(st0, 0.0).amps, st0.amps, atol=1e-14)


def test_cx_unitary() -> None:
    st = FockState.fock2(0, 1, 10)
    out = cx(st, 0.8)
    np.testing.assert_allclose(np.sum(abs(out.amps) ** 2), 1.0, atol=1e-12)


def test_cx_against_gaussian() -> None:
    from cvsim.fock.observables import mean_photon as f_mean
    from cvsim.gaussian import GaussianState
    from cvsim.gaussian import cx as g_cx

    r, g = 0.5, 0.4
    N = 24
    fst = squeeze(FockState.vacuum(N, nmode=2), r, 0)
    fst = cx(fst, g, 0, 1)
    gst = GaussianState.squeezed(r, nmode=2, mode=0)
    gst = g_cx(gst, g, 0, 1)
    for m in (0, 1):
        np.testing.assert_allclose(
            f_mean(fst, m), _gauss_mean_photon(gst, m), rtol=1e-4, atol=1e-5
        )


# -- mach_zehnder -----------------------------------------------------------


def test_mz_equals_sequential_gates() -> None:
    st = FockState.cat(10, 0.8, even=True)
    st2 = FockState.fock2(1, 0, 10)
    for st0 in (st2,):
        mz = mach_zehnder(st0, 0.6, 0.3, 0, 1)
        seq = beamsplitter(phase(beamsplitter(st0, 0.6, 0.3), 0.3, 1), np.pi / 4, 0.0)
        np.testing.assert_allclose(mz.amps, seq.amps, atol=1e-10)


def test_mz_requires_two_modes() -> None:
    with pytest.raises(ValueError):
        mach_zehnder(FockState.vacuum(8), 0.5)


# -- interferometer ---------------------------------------------------------


def test_interferometer_identity() -> None:
    st = FockState.fock2(2, 1, 8)
    np.testing.assert_allclose(interferometer(st, np.eye(2)).amps, st.amps, atol=1e-12)


def test_interferometer_matches_beamsplitter() -> None:
    theta, phi = 0.5, 0.2
    # expm(θ(e^{iφ}a0†a1 − e^{−iφ}a1†a0)) — beamsplitter convention
    U = np.array(
        [
            [np.cos(theta), np.exp(1j * phi) * np.sin(theta)],
            [-np.exp(-1j * phi) * np.sin(theta), np.cos(theta)],
        ]
    )
    st = FockState.fock2(1, 1, 10)
    np.testing.assert_allclose(
        interferometer(st, U).amps, beamsplitter(st, theta, phi).amps, atol=1e-9
    )


def test_interferometer_unitary_validation() -> None:
    st = FockState.vacuum(6, nmode=2)
    with pytest.raises(ValueError):
        interferometer(st, np.array([[1.0, 0.5], [0.0, 1.0]]))


# -- apply_unitary ----------------------------------------------------------


def test_apply_unitary_single_mode_matches_squeeze() -> None:
    from cvsim.fock.gates import _squeeze_U

    r = 0.5
    st = FockState.vacuum(10)
    out = apply_unitary(st, _squeeze_U(10, r))
    np.testing.assert_allclose(out.amps, squeeze(st, r).amps, atol=1e-12)


def test_apply_unitary_mode_selection() -> None:
    U = np.diag(np.exp(1j * np.arange(8)))  # phase gate matrix
    st = FockState.fock2(2, 3, 8)
    out1 = apply_unitary(st, U, modes=[1])
    expected = FockState.fock2(2, 3, 8)
    expected.amps[:, 3] *= np.exp(1j * 3)  # phase on mode 1
    np.testing.assert_allclose(out1.amps, expected.amps, atol=1e-12)


def test_apply_unitary_full_space() -> None:
    st = FockState.fock2(1, 0, 6)
    U = np.kron(np.diag(np.exp(1j * np.arange(6))), np.eye(6))
    out = apply_unitary(st, U)
    expected = FockState.fock2(1, 0, 6)
    expected.amps[1, 0] *= np.exp(1j)
    np.testing.assert_allclose(out.amps, expected.amps, atol=1e-12)


def test_apply_unitary_density() -> None:
    d = FockDensity.thermal(6, 0.5)
    U = np.diag(np.exp(1j * np.arange(6)))
    out = apply_unitary(d, U)
    np.testing.assert_allclose(out.rho, d.rho, atol=1e-14)  # thermal is diagonal
