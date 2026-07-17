"""Shared xxpp S must satisfy S Ω Sᵀ = Ω."""

from __future__ import annotations

import numpy as np

from cvsim.conventions import omega
from cvsim.gaussian.symplectic import S_beamsplitter, S_phase, S_squeeze


def _check_symplectic(S: np.ndarray, nmode: int) -> None:
    Om = omega(nmode)
    assert np.allclose(S @ Om @ S.T, Om, atol=1e-12)


def test_squeeze_phase_bs_symplectic():
    m = 2
    _check_symplectic(S_squeeze(m, 0.7, 0), m)
    _check_symplectic(S_phase(m, 0.3, 1), m)
    _check_symplectic(S_beamsplitter(m, 0, 1, np.pi / 4, 0.0), m)
    _check_symplectic(S_beamsplitter(m, 0, 1, 0.2, 0.4), m)
