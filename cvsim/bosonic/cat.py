"""Even/odd cat as 4 Gaussian components (ħ=1, xxpp, single mode).

Formulas follow note 04 §3.1 / arXiv:2103.05530 §IV B style:
  |cat±⟩ ∝ |α⟩ ± |-α⟩
  density needs diagonal + cross terms → 4 components.

Displacement: x = √2 Re(α), p = √2 Im(α) with α real → r = (±√2 α, 0).
Cross-term centres live on imaginary p axis: (0, ±i √2 α).
"""

from __future__ import annotations

import numpy as np

from cvsim.bosonic.state import BosonicState, Component
from cvsim.conventions import vacuum_cov


def _cat4(alpha: float, even: bool) -> BosonicState:
    if alpha <= 0:
        raise ValueError("alpha must be > 0")
    # overlap ⟨α|-α⟩ = exp(-2|α|²) for real α
    ov = np.exp(-2.0 * alpha**2)
    # pure-state weights for ρ = |ψ⟩⟨ψ| / ⟨ψ|ψ|
    # N± = 2(1 ± ov); diagonal weight each 1/N±; cross ±1/N± * phase
    # even: |ψ⟩∝|α⟩+|-α⟩,  odd: |α⟩-|-α⟩
    sign = 1.0 if even else -1.0
    # |ψ⟩ = (|α⟩ ± |-α⟩)/√N, N=2(1±ov)
    # Wigner/Gaussian-component weights (note 04): diag 1/N, cross ±ov/N
    # so ∑w = 2/N ± 2ov/N = 1
    norm = 2.0 * (1.0 + sign * ov)
    w_diag = 1.0 / norm
    w_cross = sign * ov / norm

    V = vacuum_cov(1)
    rx = np.sqrt(2.0) * alpha
    # xxpp single mode: r = (x, p)
    c0 = Component(V=V.copy(), rbar=np.array([rx, 0.0], dtype=complex), w=w_diag)
    c1 = Component(V=V.copy(), rbar=np.array([-rx, 0.0], dtype=complex), w=w_diag)
    # cross |α⟩⟨-α| and |-α⟩⟨α|: complex centres (0, ±i √2 α) in (x,p)
    c2 = Component(
        V=V.copy(),
        rbar=np.array([0.0, 1j * rx], dtype=complex),
        w=w_cross,
    )
    c3 = Component(
        V=V.copy(),
        rbar=np.array([0.0, -1j * rx], dtype=complex),
        w=w_cross,  # for real α and ±, both cross weights equal real ±1/N
    )
    return BosonicState(components=[c0, c1, c2, c3])


def even_cat(alpha: float) -> BosonicState:
    """Even cat ∝ |α⟩ + |-α⟩ as 4 components."""
    return _cat4(alpha, even=True)


def odd_cat(alpha: float) -> BosonicState:
    """Odd cat ∝ |α⟩ − |-α⟩ as 4 components."""
    return _cat4(alpha, even=False)
