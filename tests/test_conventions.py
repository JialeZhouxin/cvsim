"""Shared conventions: ħ=1, xxpp, vacuum, Ω."""

from __future__ import annotations

import numpy as np

from cvsim.conventions import HBAR, QUAD_ORDER, omega, vacuum_cov, vacuum_mean


def test_constants():
    assert HBAR == 1.0
    assert QUAD_ORDER == "xxpp"


def test_vacuum_and_omega_shapes():
    m = 3
    V = vacuum_cov(m)
    r = vacuum_mean(m)
    Om = omega(m)
    assert V.shape == (6, 6)
    assert r.shape == (6,)
    assert Om.shape == (6, 6)
    assert np.allclose(V, 0.5 * np.eye(6))
    # SΩSᵀ property for identity
    assert np.allclose(Om, -Om.T)
