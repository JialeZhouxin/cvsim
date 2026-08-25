"""Gaussian channels: V ← X V Xᵀ + Y, r̄ ← X r̄ + d.

General CPTP Gaussian channel plus named presets (loss / amplifier /
phase_noise) that special-case it. ħ=1, xxpp order.
"""

from __future__ import annotations

import numpy as np

from cvsim.conventions import omega
from cvsim.gaussian.state import GaussianState


def is_cp_channel(
    X: np.ndarray,
    Y: np.ndarray,
    *,
    atol: float = 1e-10,
) -> bool:
    """Complete-positivity check for a Gaussian channel (X, Y).

    CP condition (ħ=1, xxpp):

        Y + i Ω/2 − i X Ω Xᵀ/2  ≽ 0   (Hermitian PSD)

    The Ω/2 factor (not bare Ω) is required: the uncertainty relation is
    V + iΩ/2 ≽ 0, and the channel CP condition inherits the same ½.
    ``atol`` tolerates tiny negative eigenvalues from float64 roundoff.
    """
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    d = X.shape[0]
    if X.shape != (d, d) or Y.shape != (d, d) or d % 2 != 0:
        return False
    m = d // 2
    Omg = omega(m)
    H = Y + 1j * (Omg / 2.0) - 1j * ((X @ Omg @ X.T) / 2.0)
    H = 0.5 * (H + H.conj().T)
    w = np.linalg.eigvalsh(H)
    return bool(np.all(w >= -atol))


def validate_channel(
    X: np.ndarray,
    Y: np.ndarray,
    *,
    atol: float = 1e-10,
) -> None:
    """Raise ValueError if (X, Y) is not a CP Gaussian channel."""
    if not is_cp_channel(X, Y, atol=atol):
        raise ValueError("non-CP Gaussian channel: Y + iΩ/2 − i XΩXᵀ/2 is not PSD (ħ=1, xxpp)")


def apply_gaussian_channel(
    state: GaussianState,
    X: np.ndarray,
    Y: np.ndarray,
    d: np.ndarray | None = None,
    *,
    validate: bool = True,
) -> GaussianState:
    """Apply a general Gaussian CPTP channel (X, Y, d).

    Updates (ħ=1, xxpp):

        r̄ ← X r̄ + d
        V ← X V Xᵀ + Y

    ``validate=True`` (default) rejects non-CP (X, Y) via the condition
    ``Y + iΩ/2 − i XΩXᵀ/2 ≽ 0`` (matching the project's ``V_vac = I/2``
    convention). ``validate=False`` is a **trusted escape hatch only**: a
    non-CP pair can silently break physicality. Do not use on untrusted input.
    """
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    m = state.nmode
    if X.shape != (2 * m, 2 * m) or Y.shape != (2 * m, 2 * m):
        raise ValueError(f"X/Y must be ({2 * m},{2 * m}); got {X.shape}, {Y.shape}")
    if validate:
        validate_channel(X, Y)
    if d is None:
        d = np.zeros(2 * m)
    d = np.asarray(d, dtype=float)
    if d.shape != (2 * m,):
        raise ValueError(f"d must be ({2 * m},); got {d.shape}")

    V = X @ state.V @ X.T + Y
    rbar = X @ state.rbar + d
    V = 0.5 * (V + V.T)
    return GaussianState(V=V, rbar=rbar)


def _acted_block(
    state: GaussianState,
    modes: int | range | list | None,
) -> tuple[int, list[int]]:
    """Resolve acted modes; return (nmode, list of acted mode indices)."""
    m = state.nmode
    if modes is None:
        return m, list(range(m))
    if isinstance(modes, int):
        if not 0 <= modes < m:
            raise IndexError(f"mode {modes} out of range for nmode={m}")
        return m, [modes]
    idxs = list(modes)
    for i in idxs:
        if not 0 <= i < m:
            raise IndexError(f"mode {i} out of range for nmode={m}")
    return m, idxs


def loss(
    state: GaussianState,
    T: float,
    mode: int | None = None,
    nbar: float = 0.0,
) -> GaussianState:
    """Photon loss / attenuator with transmissivity T (ħ=1).

    Per acted mode: X = √T · I₂, Y = (1−T)(n̄+½) · I₂.
    ``mode=None`` ⇒ all modes; else single mode. ``nbar=0`` ⇒ pure loss into
    vacuum (legacy). Special case of ``apply_gaussian_channel``.
    """
    if not 0.0 <= T <= 1.0:
        raise ValueError(f"T must be in [0,1], got {T}")
    if nbar < 0.0:
        raise ValueError(f"nbar must be >= 0, got {nbar}")
    m, idxs = _acted_block(state, mode)
    X = np.eye(2 * m, dtype=float)
    Y = np.zeros((2 * m, 2 * m), dtype=float)
    sT = np.sqrt(T)
    y = (1.0 - T) * (nbar + 0.5)
    for i in idxs:
        X[i, i] = sT
        X[m + i, m + i] = sT
        Y[i, i] = y
        Y[m + i, m + i] = y
    return apply_gaussian_channel(state, X, Y, validate=False)


def amplifier(
    state: GaussianState,
    G: float,
    mode: int | None = None,
    nbar: float = 0.0,
) -> GaussianState:
    """Phase-insensitive amplifier with gain G ≥ 1 (ħ=1).

    Per acted mode: X = √G · I₂, Y = (G−1)(n̄_amp+½) · I₂.
    ``nbar=0`` ⇒ quantum-limited amplifier. ``mode=None`` ⇒ all modes.
    Special case of ``apply_gaussian_channel``.
    """
    if not G >= 1.0:
        raise ValueError(f"G must be >= 1, got {G}")
    if nbar < 0.0:
        raise ValueError(f"nbar must be >= 0, got {nbar}")
    m, idxs = _acted_block(state, mode)
    X = np.eye(2 * m, dtype=float)
    Y = np.zeros((2 * m, 2 * m), dtype=float)
    sG = np.sqrt(G)
    y = (G - 1.0) * (nbar + 0.5)
    for i in idxs:
        X[i, i] = sG
        X[m + i, m + i] = sG
        Y[i, i] = y
        Y[m + i, m + i] = y
    return apply_gaussian_channel(state, X, Y, validate=False)


def phase_noise(
    state: GaussianState,
    sigma: float,
    mode: int | None = None,
) -> GaussianState:
    """Phase diffusion via random-rotation average (ħ=1).

    Model: the mode undergoes a random phase rotation R(φ) with
    φ ∼ N(0, σ²) that is then averaged out. Averaging a Gaussian over φ
    gives a contraction X = e^{−σ²/2} · I₂ plus isotropic noise
    Y = (1 − e^{−σ²}) · ½ · I₂ on the acted mode. This is the textbook
    "phase diffusion" channel (matches Strawberry Fields / MrMustard form,
    loss-like with T = e^{−σ²}).

    ``sigma=0`` ⇒ identity. ``mode=None`` ⇒ all modes. Special case of
    ``apply_gaussian_channel``.
    """
    if sigma < 0.0:
        raise ValueError(f"sigma must be >= 0, got {sigma}")
    m, idxs = _acted_block(state, mode)
    X = np.eye(2 * m, dtype=float)
    Y = np.zeros((2 * m, 2 * m), dtype=float)
    damp = np.exp(-sigma * sigma / 2.0)
    y = (1.0 - damp * damp) * 0.5
    for i in idxs:
        X[i, i] = damp
        X[m + i, m + i] = damp
        Y[i, i] = y
        Y[m + i, m + i] = y
    return apply_gaussian_channel(state, X, Y, validate=False)
