"""Shared xxpp symplectic generators (ħ=1). Used by Gaussian + Bosonic.

Not a fourth simulator — shared foundation under G/B gates.
Prefer this module over cvsim.gaussian.symplectic (compat shim).
"""

from __future__ import annotations

import numpy as np


def d_displace(nmode: int, alpha: complex, mode: int = 0) -> np.ndarray:
    """Displacement vector d: d_x=√2 Re α, d_p=√2 Im α."""
    if not 0 <= mode < nmode:
        raise IndexError(f"mode {mode} out of range for nmode={nmode}")
    alpha = complex(alpha)
    d = np.zeros(2 * nmode, dtype=float)
    d[mode] = np.sqrt(2.0) * alpha.real
    d[nmode + mode] = np.sqrt(2.0) * alpha.imag
    return d


def S_squeeze(nmode: int, r: float, mode: int = 0) -> np.ndarray:
    """Single-mode squeeze: x→e^{-r}x, p→e^{r}p."""
    if not 0 <= mode < nmode:
        raise IndexError(f"mode {mode} out of range for nmode={nmode}")
    S = np.eye(2 * nmode)
    S[mode, mode] = np.exp(-r)
    S[nmode + mode, nmode + mode] = np.exp(r)
    return S


def S_phase(nmode: int, theta: float, mode: int = 0) -> np.ndarray:
    """Single-mode phase rotation in (x,p) plane."""
    if not 0 <= mode < nmode:
        raise IndexError(f"mode {mode} out of range for nmode={nmode}")
    c, s = np.cos(theta), np.sin(theta)
    S = np.eye(2 * nmode)
    i, p = mode, nmode + mode
    S[i, i], S[i, p] = c, -s
    S[p, i], S[p, p] = s, c
    return S


def S_beamsplitter(
    nmode: int,
    mode1: int,
    mode2: int,
    theta: float,
    phi: float = 0.0,
) -> np.ndarray:
    """Two-mode BS from unitary U embedded as xxpp symplectic.

    U = [[c, e^{iφ}s], [-e^{-iφ}s, c]], then
    S = [[Re U, -Im U], [Im U, Re U]] on the two-mode subspace.
    """
    if mode1 == mode2:
        raise ValueError("mode1 and mode2 must differ")
    for m in (mode1, mode2):
        if not 0 <= m < nmode:
            raise IndexError(f"mode {m} out of range for nmode={nmode}")

    c, s = np.cos(theta), np.sin(theta)
    eip = np.exp(1j * phi)
    # 2x2 U on (mode1, mode2)
    U = np.array(
        [[c, eip * s], [-np.conj(eip) * s, c]],
        dtype=complex,
    )
    Ru, Iu = U.real, U.imag

    # Full m x m blocks
    ReU = np.eye(nmode)
    ImU = np.zeros((nmode, nmode))
    pair = [mode1, mode2]
    for a in range(2):
        for b in range(2):
            ReU[pair[a], pair[b]] = Ru[a, b]
            ImU[pair[a], pair[b]] = Iu[a, b]

    # S = [[ReU, -ImU], [ImU, ReU]]
    return np.block([[ReU, -ImU], [ImU, ReU]])


def S_two_mode_squeeze(
    nmode: int, r: float, mode1: int, mode2: int
) -> np.ndarray:
    """Two-mode squeeze S₂(r) in xxpp (real r), EPR form.

    On (x_i, x_j, p_i, p_j):
      x_i' = ch x_i + sh x_j,  x_j' = sh x_i + ch x_j
      p_i' = ch p_i - sh p_j,  p_j' = -sh p_i + ch p_j
    Vacuum: ⟨n_i⟩=⟨n_j⟩=sinh²r; cross ⟨x_i x_j⟩, ⟨p_i p_j⟩ ≠ 0.
    """
    if mode1 == mode2:
        raise ValueError("mode1 and mode2 must differ")
    for m in (mode1, mode2):
        if not 0 <= m < nmode:
            raise IndexError(f"mode {m} out of range for nmode={nmode}")

    ch, sh = np.cosh(r), np.sinh(r)
    S = np.eye(2 * nmode)
    i, j = mode1, mode2
    pi, pj = nmode + i, nmode + j
    idx = [i, j, pi, pj]
    block = np.array(
        [
            [ch, sh, 0.0, 0.0],
            [sh, ch, 0.0, 0.0],
            [0.0, 0.0, ch, -sh],
            [0.0, 0.0, -sh, ch],
        ],
        dtype=float,
    )
    for a in range(4):
        for b in range(4):
            S[idx[a], idx[b]] = block[a, b]
    return S


def S_CZ(nmode: int, weight: float, mode1: int, mode2: int) -> np.ndarray:
    """Controlled-Z symplectic in xxpp: CZ = exp(i·weight·x̂₁·x̂₂).

    Action: x unchanged; p₁ → p₁ + weight·x₂, p₂ → p₂ + weight·x₁.
    """
    if mode1 == mode2:
        raise ValueError("mode1 and mode2 must differ")
    for m in (mode1, mode2):
        if not 0 <= m < nmode:
            raise IndexError(f"mode {m} out of range for nmode={nmode}")

    S = np.eye(2 * nmode)
    i, j = mode1, mode2
    # p_i += weight·x_j
    S[nmode + i, j] = weight
    # p_j += weight·x_i
    S[nmode + j, i] = weight
    return S


def S_CX(nmode: int, weight: float, mode1: int, mode2: int) -> np.ndarray:
    """Controlled-X symplectic in xxpp: CX = exp(-i·weight·x̂₁·p̂₂).

    Action: x₁ unchanged, x₂ → x₂ + weight·x₁;
    p₁ → p₁ - weight·p₂, p₂ unchanged.
    """
    if mode1 == mode2:
        raise ValueError("mode1 and mode2 must differ")
    for m in (mode1, mode2):
        if not 0 <= m < nmode:
            raise IndexError(f"mode {m} out of range for nmode={nmode}")

    S = np.eye(2 * nmode)
    i, j = mode1, mode2
    # x_j += weight·x_i
    S[j, i] = weight
    # p_i -= weight·p_j
    S[nmode + i, nmode + j] = -weight
    return S
