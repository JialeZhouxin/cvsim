"""Truncated |0⟩/|1⟩_GKP as Bosonic components (teaching).

1D: Dirac comb on x, spacing √(2π); V=½ diag(ε,1/ε).
2D: square lattice peaks on (x,p); V=(ε/2)I (isotropic).

|0⟩ 1d: x=kΔ;  |1⟩ 1d: x=(k+½)Δ;  k=-N…N.
|0⟩ 2d: (kΔ,lΔ); |1⟩ 2d: ((k+½)Δ, lΔ).

cross (1d only): none | nn | full.
2d: diagonal only (cross must be none). Not Gram / not Clifford.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import numpy as np

from cvsim.bosonic.state import BosonicState, Component

CrossMode = Literal["none", "nn", "full"]
LatticeMode = Literal["1d", "2d"]


def _append_cross_pair(
    comps: list[Component],
    raw_w: list[float],
    V: np.ndarray,
    x0: float,
    x1: float,
    a0: float,
    a1: float,
    epsilon: float,
) -> None:
    dx = x0 - x1
    ov = float(np.exp(-(dx * dx) / (4.0 * epsilon)))
    m = 0.5 * (x0 + x1)
    d = 0.5 * (x0 - x1)
    w_c = float(a0 * a1 * ov)
    for sign in (1.0, -1.0):
        rbar = np.array([m, 1j * sign * d], dtype=complex)
        comps.append(Component(V=V.copy(), rbar=rbar, w=0.0 + 0.0j))
        raw_w.append(w_c)


def _gkp_x_comb(
    epsilon: float,
    grid_size: int,
    *,
    cross: CrossMode,
    x_of_k: Callable[[int, float], float],
) -> BosonicState:
    if epsilon <= 0:
        raise ValueError(f"epsilon must be > 0, got {epsilon}")
    if grid_size < 0:
        raise ValueError(f"grid_size must be >= 0, got {grid_size}")
    if cross not in ("none", "nn", "full"):
        raise ValueError(f"cross must be 'none', 'nn', or 'full', got {cross!r}")

    N = int(grid_size)
    delta = np.sqrt(2.0 * np.pi)
    V = 0.5 * np.diag([epsilon, 1.0 / epsilon])
    ks = list(range(-N, N + 1))
    a = {k: np.exp(-0.5 * np.pi * epsilon * k * k) for k in ks}

    comps: list[Component] = []
    raw_w: list[float] = []

    xs = {k: float(x_of_k(k, delta)) for k in ks}
    for k in ks:
        rbar = np.array([xs[k], 0.0], dtype=complex)
        comps.append(Component(V=V.copy(), rbar=rbar, w=0.0 + 0.0j))
        raw_w.append(float(a[k] ** 2))

    if cross == "nn" and N >= 1:
        for k in range(-N, N):
            _append_cross_pair(
                comps, raw_w, V, xs[k], xs[k + 1], float(a[k]), float(a[k + 1]), epsilon
            )
    elif cross == "full":
        for i, ki in enumerate(ks):
            for kj in ks[i + 1 :]:
                _append_cross_pair(
                    comps,
                    raw_w,
                    V,
                    xs[ki],
                    xs[kj],
                    float(a[ki]),
                    float(a[kj]),
                    epsilon,
                )

    s = sum(raw_w)
    if s <= 0:
        raise ValueError("weight sum non-positive")
    for c, w in zip(comps, raw_w):
        c.w = complex(w / s)
    return BosonicState(components=comps)


def _gkp_xp_grid(
    epsilon: float,
    grid_size: int,
    *,
    cross: CrossMode,
    x_of_k: Callable[[int, float], float],
) -> BosonicState:
    """2D diagonal lattice peaks; cross must be none."""
    if epsilon <= 0:
        raise ValueError(f"epsilon must be > 0, got {epsilon}")
    if grid_size < 0:
        raise ValueError(f"grid_size must be >= 0, got {grid_size}")
    if cross != "none":
        raise ValueError("lattice='2d' supports cross='none' only (no nn/full this slice)")

    N = int(grid_size)
    delta = np.sqrt(2.0 * np.pi)
    # isotropic sharp peaks: V = (ε/2) I
    V = 0.5 * epsilon * np.eye(2, dtype=float)
    idxs = list(range(-N, N + 1))

    comps: list[Component] = []
    raw_w: list[float] = []
    for k in idxs:
        x = float(x_of_k(k, delta))
        for ell in idxs:
            p = float(ell * delta)
            # envelope on lattice indices
            amp = float(np.exp(-0.5 * np.pi * epsilon * (k * k + ell * ell)))
            rbar = np.array([x, p], dtype=complex)
            comps.append(Component(V=V.copy(), rbar=rbar, w=0.0 + 0.0j))
            raw_w.append(amp * amp)

    s = sum(raw_w)
    if s <= 0:
        raise ValueError("weight sum non-positive")
    for c, w in zip(comps, raw_w):
        c.w = complex(w / s)
    return BosonicState(components=comps)


def _dispatch(
    epsilon: float,
    grid_size: int,
    *,
    cross: CrossMode,
    lattice: LatticeMode,
    x_of_k: Callable[[int, float], float],
) -> BosonicState:
    if lattice not in ("1d", "2d"):
        raise ValueError(f"lattice must be '1d' or '2d', got {lattice!r}")
    if lattice == "1d":
        return _gkp_x_comb(epsilon, grid_size, cross=cross, x_of_k=x_of_k)
    return _gkp_xp_grid(epsilon, grid_size, cross=cross, x_of_k=x_of_k)


def gkp0(
    epsilon: float = 0.1,
    grid_size: int = 3,
    *,
    cross: CrossMode = "none",
    lattice: LatticeMode = "1d",
) -> BosonicState:
    """Approximate |0⟩_GKP.

    lattice="1d": x-teeth k=-N…N, x=kΔ; V=½diag(ε,1/ε); cross none|nn|full.
    lattice="2d": square grid (kΔ,lΔ); V=(ε/2)I; cross must be none; K=(2N+1)².
    """
    return _dispatch(
        epsilon, grid_size, cross=cross, lattice=lattice, x_of_k=lambda k, d: k * d
    )


def gkp1(
    epsilon: float = 0.1,
    grid_size: int = 3,
    *,
    cross: CrossMode = "none",
    lattice: LatticeMode = "1d",
) -> BosonicState:
    """Approximate |1⟩_GKP: half-period shift in x only vs gkp0.

    Same K / cross / lattice rules as gkp0. Teaching approx; not full Gram.
    """
    return _dispatch(
        epsilon,
        grid_size,
        cross=cross,
        lattice=lattice,
        x_of_k=lambda k, d: (k + 0.5) * d,
    )
