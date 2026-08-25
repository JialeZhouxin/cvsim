"""Interop ordering tests (Phase 6 C1): xxpp <-> xpxp permutation.

Golden values hand-derived:
- 2-mode TMSV (ħ=1), xxpp (x0,x1,p0,p1):
      V = ½[[C,S,0,0],[S,C,0,0],[0,0,C,-S],[0,0,-S,C]], C=cosh 2r, S=sinh 2r
  → xpxp (x0,p0,x1,p1) via perm [0,2,1,3]:
      V' = ½[[C,0,S,0],[0,C,0,-S],[S,0,C,0],[0,-S,0,C]]
      (per-mode diagonal blocks, x0-x1 / p0-p1 cross blocks)
- vacuum (m=3): all V = ½I in any ordering; rbar = 0.
"""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.gaussian import GaussianState, two_mode_squeeze
from cvsim.interop import from_xpxp, to_xpxp


def _random_xxpp(m: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    A = rng.normal(size=(2 * m, 2 * m))
    V = A @ A.T  # SPD, symmetric
    rbar = rng.normal(size=2 * m)
    return V, rbar


def test_roundtrip_identity_random() -> None:
    for m in (1, 2, 3):
        for seed in (0, 7):
            V, r = _random_xxpp(m, seed)
            Vb, rb = from_xpxp(*to_xpxp(V, r))
            np.testing.assert_allclose(Vb, V, atol=1e-12)
            np.testing.assert_allclose(rb, r, atol=1e-12)


def test_perm_single_mode_trivial() -> None:
    # m=1: xxpp == xpxp (x,p already adjacent)
    V, r = _random_xxpp(1, 1)
    Vb, rb = to_xpxp(V, r)
    np.testing.assert_allclose(Vb, V, atol=1e-12)
    np.testing.assert_allclose(rb, r, atol=1e-12)


def test_golden_tmsv_two_mode() -> None:
    r = 0.7
    g = two_mode_squeeze(GaussianState.vacuum(2), r, 0, 1)
    V, rbar = to_xpxp(g.V, g.rbar)
    C, S = np.cosh(2 * r), np.sinh(2 * r)
    expected = 0.5 * np.array(
        [
            [C, 0.0, S, 0.0],
            [0.0, C, 0.0, -S],
            [S, 0.0, C, 0.0],
            [0.0, -S, 0.0, C],
        ]
    )
    np.testing.assert_allclose(V, expected, atol=1e-12)
    np.testing.assert_allclose(rbar, np.zeros(4), atol=1e-12)


def test_golden_vacuum_three_mode() -> None:
    V, rbar = to_xpxp(GaussianState.vacuum(3).V, GaussianState.vacuum(3).rbar)
    np.testing.assert_allclose(V, 0.5 * np.eye(6), atol=1e-12)
    np.testing.assert_allclose(rbar, np.zeros(6), atol=1e-12)


def test_to_and_from_are_inverses_on_golden() -> None:
    r = 0.3
    g = two_mode_squeeze(GaussianState.vacuum(2), r, 0, 1)
    Vx, rx = to_xpxp(g.V, g.rbar)
    Vb, rb = from_xpxp(Vx, rx)
    np.testing.assert_allclose(Vb, g.V, atol=1e-12)
    np.testing.assert_allclose(rb, g.rbar, atol=1e-12)


@pytest.mark.parametrize(
    "V, rbar, tag",
    [
        (np.eye(3), np.zeros(3), "odd dim"),
        (np.eye(2), np.zeros(3), "rbar mismatch"),
        (np.array([[1.0, 0.5], [0.0, 1.0]]), np.zeros(2), "asymmetric"),
    ],
)
def test_validation_raises(V: np.ndarray, rbar: np.ndarray, tag: str) -> None:
    with pytest.raises(ValueError):
        to_xpxp(V, rbar)
