"""Fock analysis functions (vision §4 F2, mirror of gaussian/analyse.py):
entropy_vn / log_negativity / fidelity / partial_trace — direct Fock
spectrum, not symplectic (dense m≤2; partial_trace general m)."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from scipy.linalg import sqrtm

from cvsim.fock.density import FockDensity
from cvsim.fock.state import FockState

FockLike = FockState | FockDensity


def _to_density(state: FockLike) -> FockDensity:
    if isinstance(state, FockDensity):
        return state
    return FockDensity.from_pure(state)


def entropy_vn(state: FockLike, *, validate: bool = False) -> float:
    """Von Neumann entropy S = −Σᵢ λᵢ ln λᵢ in **nats** (Fock spectrum).

    Pure states give 0. Truncation: entropy saturates as the cutoff tail
    leaks — check with ``truncation_leakage`` for factory states.
    """
    rho = _to_density(state)
    ev = np.linalg.eigvalsh(rho.rho)
    ev = np.clip(ev, 0.0, None)
    s = -float(np.sum(ev * np.log(ev, where=ev > 0)))
    if validate and not np.isfinite(s):
        raise ValueError(f"entropy_vn: non-finite entropy {s}")
    return s


def partial_trace(
    state: FockLike, keep: int | Iterable[int]
) -> FockState | FockDensity:
    """Partial trace onto subsystem ``keep`` (mode indices).

    Drops all modes not in ``keep`` **without** measurement conditioning.
    Always returns a FockDensity (entangled pure input → mixed marginal).
    m≤2 supported (dense).
    """
    keep_list = [keep] if isinstance(keep, int) else list(keep)
    nmode = state.nmode
    if nmode == 1:
        if keep_list == [0]:
            return state
        raise IndexError(f"keep {keep_list} invalid for nmode=1")
    if nmode == 2:
        for k in keep_list:
            if k not in (0, 1):
                raise IndexError(f"mode {k} out of range for nmode=2")
        if len(keep_list) == 2:
            return state
        m = keep_list[0]
        N = state.cutoff
        if isinstance(state, FockDensity):
            rho4 = state.rho.reshape(N, N, N, N)
        else:
            rho4 = np.einsum("ab,cd->abcd", state.amps, state.amps.conj())
        red = np.einsum("abcb->ac", rho4) if m == 0 else np.einsum("abad->bd", rho4)
        return FockDensity(rho=red, nmode=1)
    raise NotImplementedError(
        f"partial_trace: nmode={nmode} not supported (dense m≤2; sparse F3)"
    )


def log_negativity(
    state: FockState | FockDensity, modes_A: int | Iterable[int]
) -> float:
    """Logarithmic negativity E_N of a bipartition (nats).

    E_N = ln ||ρ^{T_A}||₁ = ln Σᵢ |λᵢ| over the partial-transposed spectrum.
    Fock: explicit partial transpose on the (N²×N²) density, 2-mode only
    (dense anchor; sparse F3 for larger m).
    """
    modes_A = [modes_A] if isinstance(modes_A, int) else list(modes_A)
    rho = _to_density(state)
    if rho.nmode != 2:
        raise NotImplementedError("log_negativity: 2-mode only (dense anchor)")
    if sorted(modes_A) not in ([0], [1]):
        raise IndexError(f"modes_A {modes_A} invalid for nmode=2 bipartition")
    N = rho.cutoff
    rho4 = rho.rho.reshape(N, N, N, N)
    pt = np.einsum("abcd->cbad", rho4).reshape(N * N, N * N)  # PT on subsystem A only
    ev = np.linalg.eigvalsh(pt)
    return float(np.log(np.sum(np.abs(ev))))


def fidelity(
    a: FockLike,
    b: FockLike,
    *,
    rtol: float = 1e-6,
    atol: float = 1e-9,
) -> float:
    """Uhlmann fidelity F(ρ₁, ρ₂) ∈ [0, 1].

    Pure–pure: |⟨ψ|φ⟩|². Otherwise (√ρ₁ ρ₂ √ρ₁)^{1/2} trace.
    """
    if isinstance(a, FockState) and isinstance(b, FockState):
        return float(abs(np.vdot(a.amps, b.amps)) ** 2)
    ra = _to_density(a)
    rb = _to_density(b)
    if ra.nmode != rb.nmode:
        raise ValueError("fidelity: nmode mismatch")
    # truncated states may have trace < 1 (e.g. thermal): renormalize first
    ta = float(np.real(np.trace(ra.rho)))
    tb = float(np.real(np.trace(rb.rho)))
    if ta <= 0.0 or tb <= 0.0:
        raise ValueError("fidelity: non-positive input trace")
    ra = FockDensity(rho=ra.rho / ta, nmode=ra.nmode)
    rb = FockDensity(rho=rb.rho / tb, nmode=rb.nmode)
    sq = sqrtm(ra.rho)
    mid = sq @ rb.rho @ sq
    f = float(np.real(np.trace(sqrtm(mid))))
    return min(max(f * f, 0.0), 1.0)  # F = (Tr √(√ρ₁ ρ₂ √ρ₁))²
