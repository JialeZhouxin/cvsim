"""Decompose backend-guard tests — Phase 4 F-AD child 5.

Per design decision Q4: ``reck_decomposition`` /
``compose_unitary_mesh`` keep the unified ``backend=`` signature but are
**numpy-only** — ``backend="jax"`` raises ``NotImplementedError`` (honest
interface; docstring + ponytail comment mark the upgrade path).

Also locks the numpy regression: decomposition behaviour must be unchanged.
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.symplectic import (
    U_beamsplitter,
    compose_unitary_mesh,
    reck_decomposition,
)

# ---------------------------------------------------------------------------
# numpy regression: Reck round-trip unchanged
# ---------------------------------------------------------------------------


def test_reck_roundtrip_numpy() -> None:
    rng = np.random.default_rng(7)
    U, _ = np.linalg.qr(rng.normal(size=(4, 4)) + 1j * rng.normal(size=(4, 4)))
    ops = reck_decomposition(U, backend="numpy")
    U_rec = compose_unitary_mesh(4, ops, backend="numpy")
    np.testing.assert_allclose(U_rec, U, atol=1e-8)


def test_reck_returns_ops_list_numpy() -> None:
    ops = reck_decomposition(U_beamsplitter(0.4, 0.2), backend="numpy")
    assert isinstance(ops, list)
    assert len(ops) >= 2  # phases + at least one u2



# ---------------------------------------------------------------------------
# jax guard
# ---------------------------------------------------------------------------


def test_reck_jax_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="numpy"):
        reck_decomposition(U_beamsplitter(0.4, 0.2), backend="jax")



def test_compose_unitary_mesh_jax_not_implemented() -> None:
    ops = reck_decomposition(U_beamsplitter(0.4, 0.2), backend="numpy")
    with pytest.raises(NotImplementedError, match="numpy"):
        compose_unitary_mesh(2, ops, backend="jax")


# ---------------------------------------------------------------------------
# unknown backend still ValueError (not NotImplementedError)
# ---------------------------------------------------------------------------


def test_reck_unknown_backend_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown backend"):
        reck_decomposition(U_beamsplitter(0.4, 0.2), backend="torch")
