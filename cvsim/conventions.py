"""Global physical conventions for cvsim.

ħ = 1, vacuum V = I/2, quadrature order xxpp:
  r = (x_1, ..., x_m, p_1, ..., p_m)^T
  Ω = [[0, I], [-I, 0]]
"""

from __future__ import annotations

import numpy as np

HBAR = 1.0
QUAD_ORDER = "xxpp"


def omega(nmode: int) -> np.ndarray:
    """Symplectic form Ω in xxpp order, shape (2m, 2m)."""
    m = nmode
    eye = np.eye(m)
    z = np.zeros((m, m))
    return np.block([[z, eye], [-eye, z]])


def vacuum_cov(nmode: int) -> np.ndarray:
    """Vacuum covariance V = I/2, shape (2m, 2m)."""
    return 0.5 * np.eye(2 * nmode)


def vacuum_mean(nmode: int) -> np.ndarray:
    """Vacuum displacement r̄ = 0, shape (2m,)."""
    return np.zeros(2 * nmode)
