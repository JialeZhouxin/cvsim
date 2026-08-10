"""Observable-valued bridge between representations (Phase 5 F-BRIDGE).

Top-level module (ADR-0001: cross-representation code lives outside rep
packages). Converts *observables* — Fock-basis matrix elements and photon
statistics of Gaussian states — between analytic formulas and numerical
Fock states. No state conversion (no full ρ_fock): ponytail — add a complete
Gaussian→Fock state bridge when threshold post-measurement updates (or PNR
conditioning) need it.

Reference formula sources:
- coherent: ⟨n|α⟩ = e^{−|α|²/2} αⁿ/√n!
- squeezed: S(r) = exp(½r(a²−a†²)), real-r Fock convention includes
  (−1)^{n/2} (matches ``cvsim.fock.gates.squeeze``; verified numerically).
- thermal: ⟨n|ρ_th|n⟩ = n̄ⁿ/(n̄+1)^{n+1}
- vacuum prob: p₀ = exp(−½ r̄ᵀ (V+½I)⁻¹ r̄) / √det(V+½I) (single-mode, ħ=1, xxpp)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

from cvsim.conventions import omega  # noqa: F401 — convention anchor (xxpp ħ=1)

if TYPE_CHECKING:
    from cvsim.fock.state import FockState


def coherent_element(n: int, alpha: complex) -> complex:
    """Fock amplitude ⟨n|α⟩ of a coherent state (any n ≥ 0)."""
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if n == 0:
        return complex(np.exp(-abs(alpha) ** 2 / 2.0))
    return complex(
        np.exp(-abs(alpha) ** 2 / 2.0) * alpha**n / math.sqrt(math.factorial(n))
    )


def squeezed_element(n: int, r: float, phi: float = 0.0) -> complex:
    """Fock amplitude ⟨n|S(r e^{iφ})|0⟩ (real r ≥ 0).

    Convention: matches ``cvsim.fock.gates.squeeze`` (real-r) at φ=0, i.e.
    includes the (−1)^{n/2} sign for even n. Odd n → 0.
    """
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if n % 2 == 1:
        return 0.0j
    z = math.tanh(r) * np.exp(1j * phi)  # complex squeezing parameter
    m = n // 2
    pref = math.sqrt(math.factorial(2 * m)) / (
        2**m * math.factorial(m) * math.sqrt(math.cosh(r))
    )
    return complex(((-1) ** m) * pref * z**m)


def thermal_diag(n: int, nbar: float) -> float:
    """Thermal diagonal ⟨n|ρ_th|n⟩ = n̄ⁿ/(n̄+1)^{n+1}."""
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if nbar < 0.0:
        raise ValueError(f"nbar must be >= 0, got {nbar}")
    return float(nbar**n / (nbar + 1.0) ** (n + 1))


def vacuum_probability(V: np.ndarray, rbar: np.ndarray, mode: int = 0) -> float:
    """P(0) = ⟨0|ρ|0⟩ of a Gaussian state on one mode (analytic, ħ=1, xxpp).

    Reduces V to the mode's 2×2 block and r̄ to its 2-vector, then

        p₀ = exp(−½ r̄ᵀ (V+½I)⁻¹ r̄) / √det(V+½I)

    Freeze checks: vacuum → 1; coherent |α⟩ → e^{−|α|²}; thermal n̄ → 1/(n̄+1).
    """
    V = np.asarray(V, dtype=float)
    rbar = np.asarray(rbar, dtype=float)
    m = V.shape[0] // 2
    if V.shape != (2 * m, 2 * m):
        raise ValueError(f"V must be (2m, 2m); got {V.shape}")
    if rbar.shape != (2 * m,):
        raise ValueError(f"rbar must be (2m,); got {rbar.shape}")
    if not 0 <= mode < m:
        raise IndexError(f"mode {mode} out of range for nmode={m}")
    i = mode
    V1 = V[2 * i : 2 * i + 2, 2 * i : 2 * i + 2]
    r1 = rbar[2 * i : 2 * i + 2]
    A = V1 + 0.5 * np.eye(2)
    if np.linalg.eigvalsh(A).min() <= 0.0:
        raise ValueError(f"V+½I on mode {mode} is not positive-definite")
    exponent = -0.5 * float(r1 @ np.linalg.solve(A, r1))
    return float(np.exp(exponent) / np.sqrt(np.linalg.det(A)))


def fock_state_amplitude(n: int, state: FockState) -> complex:
    """Read amplitude ⟨n|ψ⟩ from a single-mode FockState (bridge test helper)."""
    amps = np.asarray(state.amps)
    if amps.ndim != 1:
        raise ValueError(f"single-mode only; got amps.ndim={amps.ndim} (ponytail)")
    if n < 0 or n >= amps.shape[0]:
        raise IndexError(f"n={n} outside cutoff={amps.shape[0]}")
    return complex(amps[n])
