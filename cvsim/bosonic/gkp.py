"""Truncated |0⟩_GKP as x-teeth Bosonic components (teaching).

Ideal |0⟩_GKP: Dirac comb on x with spacing √(2π).
Physical: V=½ diag(ε,1/ε), envelope a_k∝exp(−π ε k²/2).

cross="none": diagonal only (mixed tooth comb).
cross="nn": nearest-neighbour cross terms (partial pure-state-ish interference).
"""

from __future__ import annotations

from typing import Literal

import numpy as np

from cvsim.bosonic.state import BosonicState, Component

CrossMode = Literal["none", "nn"]


def gkp0(
    epsilon: float = 0.1,
    grid_size: int = 3,
    *,
    cross: CrossMode = "none",
) -> BosonicState:
    """Approximate |0⟩_GKP on x-axis teeth k=-N…N.

    Args:
        epsilon: tooth squeeze ε > 0; smaller → sharper x peaks.
        grid_size: N; diagonal count 2N+1; nn total K=6N+1.
        cross: "none" diagonal only; "nn" nearest-neighbour cross pairs.
    """
    if epsilon <= 0:
        raise ValueError(f"epsilon must be > 0, got {epsilon}")
    if grid_size < 0:
        raise ValueError(f"grid_size must be >= 0, got {grid_size}")
    if cross not in ("none", "nn"):
        raise ValueError(f"cross must be 'none' or 'nn', got {cross!r}")

    N = int(grid_size)
    delta = np.sqrt(2.0 * np.pi)
    V = 0.5 * np.diag([epsilon, 1.0 / epsilon])
    ks = list(range(-N, N + 1))
    # a_k ∝ exp(−π ε k² / 2); a_k² ∝ exp(−π ε k²)
    a = {k: np.exp(-0.5 * np.pi * epsilon * k * k) for k in ks}

    comps: list[Component] = []
    raw_w: list[float] = []

    for k in ks:
        rbar = np.array([k * delta, 0.0], dtype=complex)
        comps.append(Component(V=V.copy(), rbar=rbar, w=0.0 + 0.0j))
        raw_w.append(float(a[k] ** 2))

    if cross == "nn" and N >= 1:
        # ov = exp(−⅛ Δrᵀ V⁻¹ Δr) with Δr=(Δ,0), V=½diag(ε,1/ε)
        # → exp(−Δ²/(4ε)) = exp(−π/(2ε))
        ov = float(np.exp(-np.pi / (2.0 * epsilon)))
        for k in range(-N, N):
            x0 = k * delta
            x1 = (k + 1) * delta
            m = 0.5 * (x0 + x1)
            d = 0.5 * (x0 - x1)  # = −Δ/2
            w_c = float(a[k] * a[k + 1] * ov)
            for sign in (1.0, -1.0):
                rbar = np.array([m, 1j * sign * d], dtype=complex)
                comps.append(Component(V=V.copy(), rbar=rbar, w=0.0 + 0.0j))
                raw_w.append(w_c)

    s = sum(raw_w)
    if s <= 0:
        raise ValueError("weight sum non-positive")
    for c, w in zip(comps, raw_w):
        c.w = complex(w / s)
    return BosonicState(components=comps)
