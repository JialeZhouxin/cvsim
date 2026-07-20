"""Truncated |0⟩_GKP as diagonal x-teeth Bosonic components (teaching approx).

Ideal |0⟩_GKP: Dirac comb on x with spacing √(2π).
Physical: narrow pure Gaussians V=½ diag(ε,1/ε), envelope w∝exp(−π ε k²).

No p-teeth / cross terms → diagonal tooth comb, not full pure GKP.
"""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.state import BosonicState, Component


def gkp0(epsilon: float = 0.1, grid_size: int = 3) -> BosonicState:
    """Approximate |0⟩_GKP on x-axis teeth k=-N…N.

    Args:
        epsilon: tooth squeeze ε ∈ (0, 1]; smaller → sharper x peaks.
        grid_size: N; component count K = 2N+1.
    """
    if epsilon <= 0:
        raise ValueError(f"epsilon must be > 0, got {epsilon}")
    if grid_size < 0:
        raise ValueError(f"grid_size must be >= 0, got {grid_size}")

    N = int(grid_size)
    delta = np.sqrt(2.0 * np.pi)
    V = 0.5 * np.diag([epsilon, 1.0 / epsilon])

    ks = range(-N, N + 1)
    raw = [np.exp(-np.pi * epsilon * k * k) for k in ks]
    s = sum(raw)
    comps: list[Component] = []
    for k, w in zip(ks, raw):
        rbar = np.array([k * delta, 0.0], dtype=complex)
        comps.append(Component(V=V.copy(), rbar=rbar, w=complex(w / s)))
    return BosonicState(components=comps)
