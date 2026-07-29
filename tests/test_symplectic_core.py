"""F-SYMPLECTIC-CORE: is_symplectic, validate, apply_symplectic."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import GaussianState, apply_symplectic, det_cov, displace, squeeze
from cvsim.symplectic import (
    S_phase,
    S_squeeze,
    d_displace,
    is_symplectic,
    validate_symplectic,
)


def test_identity_is_symplectic():
    assert is_symplectic(np.eye(2))
    assert is_symplectic(np.eye(4))


def test_library_generators_symplectic():
    assert is_symplectic(S_squeeze(1, 0.7, 0))
    assert is_symplectic(S_phase(2, 0.3, 1))
    S = S_phase(2, 0.2, 0) @ S_squeeze(2, 0.5, 1)
    assert is_symplectic(S)


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
    S = np.array([[2.0, 0.0], [0.0, 0.5]])  # still det-ish but not symplectic check path
    # non-symplectic scale
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
