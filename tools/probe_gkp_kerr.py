"""Probe: Fock — does squeeze→kerr evolve vacuum toward GKP (position comb)?

Judge via the x-marginal probability density P(x) = |⟨x|ψ⟩|² (positive, clean),
which for a GKP |0⟩_1d is a comb: peaks at x = kΔ, Δ=√(2π)≈2.507.

Hermite basis: ⟨x|n⟩ = (1/π^{1/4}) · e^{-x²/2} H_n(x) / √(2^n n!)  (ħ=1).
"""

from __future__ import annotations

import warnings

import math

import numpy as np

warnings.filterwarnings("ignore")

from cvsim.fock import FockState
from cvsim.fock.gates import squeeze, kerr, displace, phase
from scipy.special import eval_hermite

DELTA = np.sqrt(2.0 * np.pi)  # GKP x-lattice constant


def x_amplitude(n: int, x: float) -> float:
    """⟨x|n⟩ real harmonic-oscillator wavefunction (ħ=1)."""
    return float(
        np.exp(-x * x / 2.0)
        * eval_hermite(n, x)
        / np.sqrt(2.0**n * float(math.factorial(n)))
        / np.pi**0.25
    )


def x_marginal(amps: np.ndarray, xs: np.ndarray) -> np.ndarray:
    """P(x) = |Σ_n amps_n ⟨x|n⟩|² for a single-mode Fock state."""
    # matrix of ⟨x|n⟩, shape (len(xs), len(amps))
    M = np.array([[x_amplitude(n, x) for n in range(len(amps))] for x in xs])
    return np.abs(M @ amps) ** 2


def comb_score(P: np.ndarray, xs: np.ndarray) -> dict:
    """Score how comb-like P(x) is: #peaks + peak regularity + envelope."""
    if len(P) < 3:
        return {"peaks": 0, "peak_spacing": np.nan, "contrast": 0.0}
    # local maxima
    pk = np.where((P[1:-1] > P[:-2]) & (P[1:-1] >= P[2:]))[0] + 1
    # central-most peaks > half of global max
    thr = 0.5 * P.max()
    big = [i for i in pk if P[i] > thr]
    spacing = np.median(np.diff(xs[big])) if len(big) > 1 else np.nan
    contrast = float((P.max() - P.min()) / (P.max() + 1e-12))
    return {"peaks": len(big), "peak_spacing": spacing, "contrast": contrast}


def main() -> None:
    N = 40  # Fock cutoff (enough for r ≤ ~1.3)
    xs = np.linspace(-4.5, 4.5, 601)

    print("=" * 74)
    print("Route A — deterministic Kerr: squeeze(r) → kerr(chi) → squeeze(-r)")
    print("   (target: x-comb with peaks at x=k·Δ, Δ=√(2π)≈%.3f)" % DELTA)
    print("=" * 74)

    vac = FockState.vacuum(N)

    # Reference: ideal-ish comb candidate = a squeezed vacuum with NO kerr (Gaussian).
    # A GKP needs interference; kerr supplies it. Baseline for each r:
    results = []
    for r in (0.8, 1.0, 1.2):
        for chi in (0.2, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0, 3.0):
            sq = squeeze(vac, r)
            k = kerr(sq, chi)
            usq = squeeze(k, -r)  # unsqueeze
            P = x_marginal(usq.amps, xs)
            s = comb_score(P, xs)
            results.append((r, chi, s))
            print(f"  r={r:.1f} chi={chi:.1f}: peaks={s['peaks']} "
                  f"spacing={s['peak_spacing'] if s['peaks']>1 else float('nan'):.2f} "
                  f"contrast={s['contrast']:.2f}")

    # Best candidates by contrast (comb should be deep = high contrast)
    print()
    print("--- top candidates by contrast ---")
    for r, chi, s in sorted(results, key=lambda t: -t[2]["contrast"])[:8]:
        print(f"  r={r} chi={chi}: contrast={s['contrast']:.3f} peaks={s['peaks']}")


if __name__ == "__main__":
    main()
