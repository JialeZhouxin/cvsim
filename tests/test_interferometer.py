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
    compose_unitary_mesh,
    is_symplectic,
    is_unitary,
    reck_decomposition,
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



def test_apply_mesh_matches_interferometer():
    rng = np.random.default_rng(3)
    m = 4
    U = _haar_unitary(m, rng)
    st0 = GaussianState.squeezed(0.4, nmode=m, mode=0)
    via_U = interferometer(st0, U)
    via_mesh = apply_mesh(st0, reck_decomposition(U))
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
    np.testing.assert_allclose(fourier(st).V, phase(st, 0.5 * np.pi).V, atol=1e-12)


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
        __import__("cvsim.gaussian.gates", fromlist=["apply_symplectic"])
        .apply_symplectic(st, S_mach_zehnder(2, 0, 1, theta, phi), validate=False)
        .V,
        atol=1e-12,
    )


def test_interferometer_shape_mismatch():
    with pytest.raises(ValueError, match="shape"):
        interferometer(GaussianState.vacuum(2), np.eye(3, dtype=complex))


def test_homomorphism_S_from_unitary():
    rng = np.random.default_rng(4)
    for m in (2, 3, 4):
        U1, U2 = _haar_unitary(m, rng), _haar_unitary(m, rng)
        S12 = S_from_unitary(U2 @ U1)
        S_prod = S_from_unitary(U2) @ S_from_unitary(U1)
        np.testing.assert_allclose(S12, S_prod, atol=1e-10)


def test_passive_S_orthogonal_and_det_one():
    rng = np.random.default_rng(5)
    for m in (1, 2, 4):
        U = _haar_unitary(m, rng)
        S = S_from_unitary(U)
        np.testing.assert_allclose(S.T @ S, np.eye(2 * m), atol=1e-10)
        np.testing.assert_allclose(np.linalg.det(S), 1.0, atol=1e-8)


def test_total_photon_conserved_under_interferometer():
    from cvsim.gaussian import mean_photon

    rng = np.random.default_rng(6)
    m = 3
    st = GaussianState.product(
        GaussianState.squeezed(0.5),
        GaussianState.coherent(0.4 + 0.1j),
        GaussianState.thermal(0.2),
    )
    n0 = mean_photon(st)
    U = _haar_unitary(m, rng)
    n1 = mean_photon(interferometer(st, U))
    np.testing.assert_allclose(n1, n0, atol=1e-12)


def test_fourier_quadrant_map():
    # coherent α real → after F: mean goes to p axis (x→-p, p→x) with S_phase(π/2)
    st = GaussianState.coherent(0.5 + 0.0j)
    out = fourier(st)
    # S_phase(π/2): x' = -p, p' = x  => rbar' = (0, √2*0.5)
    np.testing.assert_allclose(out.rbar[0], 0.0, atol=1e-12)
    np.testing.assert_allclose(out.rbar[1], np.sqrt(2) * 0.5, atol=1e-12)


def test_large_m_smoke_and_reck_residual():
    rng = np.random.default_rng(7)
    m = 16
    U = _haar_unitary(m, rng)
    S = S_from_unitary(U)
    assert is_symplectic(S, atol=1e-7)
    st = interferometer(GaussianState.vacuum(m), U)
    np.testing.assert_allclose(det_cov(st), (0.25) ** m, atol=1e-8)
    ops = reck_decomposition(U)
    err = np.linalg.norm(compose_unitary_mesh(m, ops) - U)
    assert err < 1e-8
    # Reck u2 count
    n_u2 = sum(1 for o in ops if o[0] == "u2")
    assert n_u2 == m * (m - 1) // 2


def test_circuit_fourier_mz_interferometer():
    from cvsim.gaussian import GaussianCircuit, mean_photon

    c = GaussianCircuit(2)
    c.squeeze(0, r=0.4)
    c.fourier(0)
    c.mach_zehnder(0, 1, theta=np.pi / 4, phi=0.2)
    st = c.run()
    assert st.nmode == 2
    assert mean_photon(st) > 0

    U = U_beamsplitter(np.pi / 4, 0.0)
    c2 = GaussianCircuit(2)
    c2.two_mode_squeeze(0, 1, r=0.3)
    c2.interferometer(U)
    st2 = c2.run()
    direct = interferometer(GaussianState.tmsv(0.3), U)
    np.testing.assert_allclose(st2.V, direct.V, atol=1e-12)
