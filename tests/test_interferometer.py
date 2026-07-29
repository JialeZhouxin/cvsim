"""F-INTERFEROMETER + fourier / mach_zehnder."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import (
    GaussianState,
    apply_mesh,
    beamsplitter,
    det_cov,
    fourier,
    interferometer,
    mach_zehnder,
    phase,
)
from cvsim.symplectic import (
    S_beamsplitter,
    S_from_unitary,
    S_mach_zehnder,
    S_phase,
    U_beamsplitter,
    clements_decomposition,
    compose_unitary_mesh,
    is_symplectic,
    is_unitary,
    reck_decomposition,
    validate_unitary,
)


def _haar_unitary(m: int, rng: np.random.Generator) -> np.ndarray:
    z = rng.normal(size=(m, m)) + 1j * rng.normal(size=(m, m))
    q, r = np.linalg.qr(z)
    d = np.diag(r)
    ph = d / np.abs(d)
    return q * ph


def test_S_from_unitary_identity():
    S = S_from_unitary(np.eye(3, dtype=complex))
    np.testing.assert_allclose(S, np.eye(6), atol=1e-14)
    assert is_symplectic(S)


def test_S_from_unitary_rejects_non_unitary():
    with pytest.raises(ValueError, match="unitary"):
        S_from_unitary(np.array([[1.0, 1.0], [0.0, 1.0]], dtype=complex))


def test_S_from_unitary_matches_beamsplitter():
    theta, phi = 0.37, 0.55
    S_bs = S_beamsplitter(2, 0, 1, theta, phi)
    U = np.eye(2, dtype=complex)
    U[np.ix_([0, 1], [0, 1])] = U_beamsplitter(theta, phi)
    S_u = S_from_unitary(U)
    np.testing.assert_allclose(S_bs, S_u, atol=1e-12)


def test_S_from_unitary_matches_S_phase_sign():
    theta = 0.42
    U = np.array([[np.exp(1j * theta)]], dtype=complex)
    np.testing.assert_allclose(S_from_unitary(U), S_phase(1, theta, 0), atol=1e-12)


def test_haar_unitary_symplectic_and_purity():
    rng = np.random.default_rng(1)
    for m in (2, 4, 8):
        for _ in range(5):
            U = _haar_unitary(m, rng)
            assert is_unitary(U)
            S = S_from_unitary(U)
            assert is_symplectic(S, atol=1e-8)
            st = interferometer(GaussianState.vacuum(m), U)
            np.testing.assert_allclose(det_cov(st), (0.25) ** m, atol=1e-10)
            np.testing.assert_allclose(st.V, 0.5 * np.eye(2 * m), atol=1e-10)


def test_reck_roundtrip():
    rng = np.random.default_rng(2)
    for m in (2, 3, 4, 5):
        U = _haar_unitary(m, rng)
        ops = reck_decomposition(U)
        U2 = compose_unitary_mesh(m, ops)
        assert np.linalg.norm(U2 - U) < 1e-8
        # alias
        ops_c = clements_decomposition(U)
        U3 = compose_unitary_mesh(m, ops_c)
        assert np.linalg.norm(U3 - U) < 1e-8


def test_apply_mesh_matches_interferometer():
    rng = np.random.default_rng(3)
    m = 4
    U = _haar_unitary(m, rng)
    st0 = GaussianState.squeezed(0.4, nmode=m, mode=0)
    via_U = interferometer(st0, U)
    via_mesh = apply_mesh(st0, clements_decomposition(U))
    np.testing.assert_allclose(via_U.V, via_mesh.V, atol=1e-9)
    np.testing.assert_allclose(via_U.rbar, via_mesh.rbar, atol=1e-9)


def test_tmsv_plus_balanced_bs():
    # interferometer equal to 50:50 BS
    U = U_beamsplitter(np.pi / 4, 0.0)
    st = GaussianState.tmsv(0.5)
    a = interferometer(st, U)
    b = beamsplitter(st, 0, 1, np.pi / 4, 0.0)
    np.testing.assert_allclose(a.V, b.V, atol=1e-12)


def test_fourier_four_times_identity():
    st = GaussianState.displaced_squeezed(0.3 + 0.2j, r=0.35, phi=0.1)
    out = st
    for _ in range(4):
        out = fourier(out, mode=0)
    np.testing.assert_allclose(out.V, st.V, atol=1e-12)
    np.testing.assert_allclose(out.rbar, st.rbar, atol=1e-12)
    # one fourier == phase(pi/2)
    np.testing.assert_allclose(
        fourier(st).V, phase(st, 0.5 * np.pi).V, atol=1e-12
    )


def test_mach_zehnder_matches_manual():
    st = GaussianState.squeezed(0.3, nmode=2, mode=0)
    theta, phi = 0.31, 0.77
    via_gate = mach_zehnder(st, 0, 1, theta, phi)
    manual = beamsplitter(st, 0, 1, theta, 0.0)
    manual = phase(manual, phi, mode=0)
    manual = beamsplitter(manual, 0, 1, np.pi / 4, 0.0)
    np.testing.assert_allclose(via_gate.V, manual.V, atol=1e-12)
    np.testing.assert_allclose(
        via_gate.V,
        __import__("cvsim.gaussian.gates", fromlist=["apply_symplectic"]).apply_symplectic(
            st, S_mach_zehnder(2, 0, 1, theta, phi), validate=False
        ).V,
        atol=1e-12,
    )


def test_interferometer_shape_mismatch():
    with pytest.raises(ValueError, match="shape"):
        interferometer(GaussianState.vacuum(2), np.eye(3, dtype=complex))
