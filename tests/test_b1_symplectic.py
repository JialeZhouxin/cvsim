"""Shared xxpp S must satisfy S Ω Sᵀ = Ω."""

from __future__ import annotations

import numpy as np
import pytest

from cvsim.conventions import omega
from cvsim.symplectic import S_CX, S_CZ, S_beamsplitter, S_phase, S_squeeze


def _check_symplectic(S: np.ndarray, nmode: int) -> None:
    Om = omega(nmode)
    assert np.allclose(S @ Om @ S.T, Om, atol=1e-12)


def test_squeeze_phase_bs_symplectic():
    m = 2
    _check_symplectic(S_squeeze(m, 0.7, 0), m)
    _check_symplectic(S_phase(m, 0.3, 1), m)
    _check_symplectic(S_beamsplitter(m, 0, 1, np.pi / 4, 0.0), m)
    _check_symplectic(S_beamsplitter(m, 0, 1, 0.2, 0.4), m)


def test_cz_symplectic():
    """S_CZ must be symplectic and reproduce correct action."""
    m = 2
    S = S_CZ(m, 0.5, 0, 1)
    _check_symplectic(S, m)
    # p₁ += g·x₂: S[nmode+mode1, mode2] = g
    assert S[2, 1] == 0.5
    # p₂ += g·x₁: S[nmode+mode2, mode1] = g
    assert S[3, 0] == 0.5
    # x unchanged
    assert S[0, 0] == 1 and S[1, 1] == 1
    # identity elsewhere (spot check)
    assert S[0, 1] == 0 and S[1, 0] == 0


def test_cx_symplectic():
    """S_CX must be symplectic and reproduce correct action."""
    m = 2
    S = S_CX(m, 0.3, 0, 1)
    _check_symplectic(S, m)
    # x₂ += g·x₁: S[mode2, mode1] = g
    assert S[1, 0] == 0.3
    # p₁ -= g·p₂: S[nmode+mode1, nmode+mode2] = -g
    assert S[2, 3] == -0.3
    # x₁, p₂ unchanged
    assert S[0, 0] == 1 and S[3, 3] == 1


def test_cz_cx_validation():
    """S_CZ and S_CX raise on same-mode or out-of-range."""
    with pytest.raises(ValueError, match="must differ"):
        S_CZ(2, 0.5, 0, 0)
    with pytest.raises(ValueError, match="must differ"):
        S_CX(2, 0.5, 1, 1)
    with pytest.raises(IndexError):
        S_CZ(2, 0.5, 0, 2)
    with pytest.raises(IndexError):
        S_CX(2, 0.5, -1, 0)
