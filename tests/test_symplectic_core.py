"""F-SYMPLECTIC-CORE: is_symplectic, validate, apply_symplectic."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import (
    GaussianState,
    apply_symplectic,
    det_cov,
    displace,
    squeeze,
)
from cvsim.symplectic import (
    S_CX,
    S_CZ,
    S_beamsplitter,
    S_phase,
    S_squeeze,
    S_two_mode_squeeze,
    d_displace,
    is_symplectic,
    validate_symplectic,
)


def _random_symplectic(m: int, rng: np.random.Generator) -> np.ndarray:
    """Compose random library gates into an Sp(2m) element."""
    S = np.eye(2 * m)
    for _ in range(8):
        which = int(rng.integers(0, 4))
        if which == 0:
            mode = int(rng.integers(0, m))
            S = S_squeeze(m, float(rng.normal(scale=0.4)), mode) @ S
        elif which == 1:
            mode = int(rng.integers(0, m))
            S = S_phase(m, float(rng.uniform(0, 2 * np.pi)), mode) @ S
        elif which == 2 and m >= 2:
            i, j = rng.choice(m, size=2, replace=False)
            S = (
                S_beamsplitter(
                    m, int(i), int(j), float(rng.uniform(0, np.pi / 2)), float(rng.uniform(0, 2 * np.pi))
                )
                @ S
            )
        elif which == 3 and m >= 2:
            i, j = rng.choice(m, size=2, replace=False)
            if rng.random() < 0.5:
                S = S_CZ(m, float(rng.normal(scale=0.5)), int(i), int(j)) @ S
            else:
                S = S_CX(m, float(rng.normal(scale=0.5)), int(i), int(j)) @ S
        else:
            mode = int(rng.integers(0, m))
            S = S_squeeze(m, float(rng.normal(scale=0.3)), mode) @ S
    return S


def test_identity_is_symplectic():
    assert is_symplectic(np.eye(2))
    assert is_symplectic(np.eye(4))


def test_library_generators_symplectic():
    assert is_symplectic(S_squeeze(1, 0.7, 0))
    assert is_symplectic(S_phase(2, 0.3, 1))
    assert is_symplectic(S_CZ(2, 0.4, 0, 1))
    assert is_symplectic(S_CX(2, 0.4, 0, 1))
    assert is_symplectic(S_two_mode_squeeze(2, 0.5, 0, 1))
    S = S_phase(2, 0.2, 0) @ S_squeeze(2, 0.5, 1)
    assert is_symplectic(S)


def test_random_symplectic_property():
    rng = np.random.default_rng(0)
    for m in (1, 2, 3):
        for _ in range(20):
            S = _random_symplectic(m, rng)
            assert is_symplectic(S, atol=1e-8)


def test_broken_S_not_symplectic():
    S = np.eye(2)
    S[0, 0] = 2.0
    assert not is_symplectic(S)
    with pytest.raises(ValueError, match="symplectic"):
        validate_symplectic(S)


def test_apply_rejects_bad_S():
    st = GaussianState.vacuum(1)
    S = np.array([[2.0, 0.0], [0.0, 1.0]])
    with pytest.raises(ValueError, match="symplectic"):
        apply_symplectic(st, S, validate=True)


def test_apply_validate_false_allows_bad_S():
    st = GaussianState.vacuum(1)
    Sbad = np.array([[2.0, 0.0], [0.0, 1.0]])
    out = apply_symplectic(st, Sbad, validate=False)
    assert out.V.shape == (2, 2)


def test_apply_matches_squeeze_and_displace():
    st = GaussianState.vacuum(1)
    r = 0.4
    alpha = 0.3 + 0.2j
    via_S = apply_symplectic(st, S_squeeze(1, r, 0), validate=True)
    via_gate = squeeze(st, r)
    np.testing.assert_allclose(via_S.V, via_gate.V, atol=1e-12)

    via_d = apply_symplectic(
        st, np.eye(2), d_displace(1, alpha, 0), validate=True
    )
    via_disp = displace(st, alpha)
    np.testing.assert_allclose(via_d.rbar, via_disp.rbar, atol=1e-12)


def test_squeeze_gate_phi_matches_factory():
    r, phi = 0.45, 0.8
    via_gate = squeeze(GaussianState.vacuum(1), r, phi=phi)
    via_fac = GaussianState.squeezed(r, phi=phi)
    np.testing.assert_allclose(via_gate.V, via_fac.V, atol=1e-12)


def test_pure_state_det_preserved_under_symplectic():
    st = squeeze(GaussianState.vacuum(2), 0.5, mode=0)
    det0 = det_cov(st)
    S = S_phase(2, 0.7, 1) @ S_squeeze(2, 0.3, 0)
    assert is_symplectic(S)
    out = apply_symplectic(st, S, validate=True)
    np.testing.assert_allclose(det_cov(out), det0, atol=1e-10)
    np.testing.assert_allclose(det_cov(out), (0.25) ** 2, atol=1e-10)


def test_shape_mismatch():
    st = GaussianState.vacuum(1)
    with pytest.raises(ValueError, match="shape"):
        apply_symplectic(st, np.eye(4), validate=False)


def test_d_shape_mismatch():
    st = GaussianState.vacuum(1)
    with pytest.raises(ValueError, match="d shape"):
        apply_symplectic(st, np.eye(2), d=np.zeros(4), validate=False)


def test_apply_does_not_mutate_input():
    st = GaussianState.coherent(0.4 + 0.1j)
    V0 = st.V.copy()
    r0 = st.rbar.copy()
    S = S_squeeze(1, 0.3, 0)
    _ = apply_symplectic(st, S, validate=True)
    np.testing.assert_array_equal(st.V, V0)
    np.testing.assert_array_equal(st.rbar, r0)


def test_compat_shim_exports_match_main():
    import cvsim.gaussian.symplectic as shim
    import cvsim.symplectic as main

    for name in shim.__all__:
        assert hasattr(main, name), name
        assert getattr(shim, name) is getattr(main, name), name

    assert "is_symplectic" in shim.__all__
    assert "validate_symplectic" in shim.__all__
    assert "S_CZ" in shim.__all__
    assert "S_CX" in shim.__all__
    assert shim.is_symplectic(np.eye(2))
