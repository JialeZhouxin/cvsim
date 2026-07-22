"""Truncated |0⟩/|1⟩_GKP as x-teeth Bosonic components (teaching).

Ideal: Dirac comb on x with spacing √(2π).
|0⟩: x = k Δ;  |1⟩: x = (k+½) Δ;  k = -N…N.
Physical: V=½ diag(ε,1/ε), envelope a_k∝exp(−π ε k²/2).

cross="none": diagonal only (mixed tooth comb).
cross="nn": nearest-neighbour cross terms.
cross="full": all tooth pairs (full-pair interference on 1D comb).
Not full Gram orthog / not 2D lattice pure GKP.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import numpy as np

from cvsim.bosonic.state import BosonicState, Component

CrossMode = Literal["none", "nn", "full"]


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
    # a_k ∝ exp(−π ε k² / 2); index k for envelope (same for |0⟩/|1⟩)
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


def gkp0(
    epsilon: float = 0.1,
    grid_size: int = 3,
    *,
    cross: CrossMode = "none",
) -> BosonicState:
    """Approximate |0⟩_GKP on x-axis teeth k=-N…N, x=kΔ.

    Args:
        epsilon: tooth squeeze ε > 0; smaller → sharper x peaks.
        grid_size: N; diagonal count 2N+1; nn total K=6N+1; full K=(2N+1)².
        cross: "none" diagonal; "nn" nearest-neighbour; "full" all pairs.
    """
    return _gkp_x_comb(
        epsilon, grid_size, cross=cross, x_of_k=lambda k, d: k * d
    )


def gkp1(
    epsilon: float = 0.1,
    grid_size: int = 3,
    *,
    cross: CrossMode = "none",
) -> BosonicState:
    """Approximate |1⟩_GKP: same comb as gkp0 but peaks at x=(k+½)Δ.

    Same K and envelope as gkp0 for fixed N. Teaching approx; not full Gram.
    """
    return _gkp_x_comb(
        epsilon, grid_size, cross=cross, x_of_k=lambda k, d: (k + 0.5) * d
    )
