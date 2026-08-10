"""Backend-parameterised validation tests — Phase 4 F-AD child 4.

Covers ``is_symplectic`` / ``validate_symplectic`` / ``is_unitary`` /
``validate_unitary`` backend= paths:

- known symplectic / non-symplectic matrices judged identically on np/jax
- error paths (non-square, odd dimension, invalid values) consistent
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim import backend as be
from cvsim.symplectic import (
    S_beamsplitter,
    S_squeeze,
    U_beamsplitter,
    is_symplectic,
    is_unitary,
    validate_symplectic,
    validate_unitary,
)


def _arr(backend: str, a: np.ndarray) -> np.ndarray:
    """Convert numpy array to the backend's array type."""
    xp = be._get_xp(backend)
    return xp.asarray(a)


def _squeeze_symplectic() -> np.ndarray:
    return S_squeeze(2, 0.3, 0)


def _not_symplectic() -> np.ndarray:
    return np.array(
        [[1.0, 0.0, 0.0, 0.0], [0.0, 2.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
    )


def _bs_unitary() -> np.ndarray:
    return U_beamsplitter(0.4, 0.2)


def _not_unitary() -> np.ndarray:
    return np.array([[1.0, 0.5], [0.0, 1.0]], dtype=complex)


# ---------------------------------------------------------------------------
# is_symplectic
# ---------------------------------------------------------------------------


def test_is_symplectic_true(backend: str) -> None:
    S = _arr(backend, _squeeze_symplectic())
    assert is_symplectic(S, backend=backend)


def test_is_symplectic_false(backend: str) -> None:
    S = _arr(backend, _not_symplectic())
    assert not is_symplectic(S, backend=backend)


def test_is_symplectic_bs_true(backend: str) -> None:
    S = _arr(backend, S_beamsplitter(2, 0, 1, 0.4, 0.2))
    assert is_symplectic(S, backend=backend)


def test_is_symplectic_non_square(backend: str) -> None:
    S = _arr(backend, np.eye(4)[:, :2])
    assert not is_symplectic(S, backend=backend)


def test_is_symplectic_odd_dim(backend: str) -> None:
    S = _arr(backend, np.eye(3))
    assert not is_symplectic(S, backend=backend)


# ---------------------------------------------------------------------------
# validate_symplectic
# ---------------------------------------------------------------------------


def test_validate_symplectic_ok(backend: str) -> None:
    S = _arr(backend, _squeeze_symplectic())
    validate_symplectic(S, backend=backend)  # no raise


def test_validate_symplectic_raises(backend: str) -> None:
    S = _arr(backend, _not_symplectic())
    with pytest.raises(ValueError, match="not symplectic"):
        validate_symplectic(S, backend=backend)


def test_validate_symplectic_non_square_raises(backend: str) -> None:
    S = _arr(backend, np.eye(4)[:, :2])
    with pytest.raises(ValueError, match="square"):
        validate_symplectic(S, backend=backend)


# ---------------------------------------------------------------------------
# is_unitary
# ---------------------------------------------------------------------------


def test_is_unitary_true(backend: str) -> None:
    U = _arr(backend, _bs_unitary())
    assert is_unitary(U, backend=backend)


def test_is_unitary_false(backend: str) -> None:
    U = _arr(backend, _not_unitary())
    assert not is_unitary(U, backend=backend)


def test_is_unitary_non_square(backend: str) -> None:
    U = _arr(backend, np.eye(2)[:, :1])
    assert not is_unitary(U, backend=backend)


# ---------------------------------------------------------------------------
# validate_unitary
# ---------------------------------------------------------------------------


def test_validate_unitary_ok(backend: str) -> None:
    U = _arr(backend, _bs_unitary())
    validate_unitary(U, backend=backend)  # no raise


def test_validate_unitary_raises(backend: str) -> None:
    U = _arr(backend, _not_unitary())
    with pytest.raises(ValueError, match="not unitary"):
        validate_unitary(U, backend=backend)


def test_validate_unitary_non_square_raises(backend: str) -> None:
    U = _arr(backend, np.eye(2)[:, :1])
    with pytest.raises(ValueError, match="square"):
        validate_unitary(U, backend=backend)
