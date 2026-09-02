"""Probe: Fock — two-mode entanglement + PNR/homodyne → conditional displace → GKP?

Standard GKP preparation schemes build the position-comb via a correlated
two-mode state + a measurement on one mode that projects the other toward a
comb. We try the common family:
    two_mode_squeeze(r)  →  [measure ancilla mode 1]  →  displace(mode0, ParamRef)

The leftover mode-0 x-marginal is scored for comb structure. We scan r and the
measurement type (PNR photon-number, homodyne-x), across many shots, and look
for a post-selected mode-0 state whose x-marginal is comb-like.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

warnings.filterwarnings("ignore")

from cvsim.fock import FockState
from cvsim.fock.circuit import FockCircuit
from cvsim.wigner import wigner_fock
from cvsim.fock.observables import homodyne_sample

DELTA = np.sqrt(2.0 * np.pi)


def comb_score(P: np.ndarray) -> tuple[int, float, float]:
    if len(P) < 3:
        return 0, float("nan"), 0.0
    pk = np.where((P[1:-1] > P[:-2]) & (P[1:-1] >= P[2:]))[0] + 1
    thr = 0.5 * P.max()
    big = [i for i in pk if P[i] > thr]
    spacing = float(np.median(np.diff(big))) if len(big) > 1 else float("nan")
    contrast = float((P.max() - P.min()) / (P.max() + 1e-12))
    return len(big), spacing, contrast


def main() -> None:
    N = 14  # cutoff for two-mode (K² blowup; keep small)
    xs = np.linspace(-5.0, 5.0, 401)

    print("=" * 74)
    print("Route B — two-mode squeeze + homodyne-x ancilla → condition mode 0")
    print("   (ideal GKP needs r→large + high-fidelity projection; scan r)")
    print("=" * 74)

    for r in (0.5, 0.8, 1.0, 1.2):
        # Build: tms → homodyne measure mode1 → keep mode0
        c = FockCircuit(2, cutoff=N)
        c.two_mode_squeeze(0, 1, r)
        c.measure_homodyne(1, phi=0.0, name="m_x")  # phi=0 → measure x of mode1
        best_spacing = []
        state, results = c.run()
        # state is now 1-mode (mode 0 post-measurement), results['m_x'] = x
        # score its x-marginal via Wigner-over-p or Fock |ψ(x)|²:
        # use x-marginal from Fock amps
        amps = state.amps
        M = np.array(
            [
                [
                    float(
                        np.exp(-x * x / 2) * math.erf(0)  # placeholder, replaced below
                    )
                    for _ in range(len(amps))
                ]
                for x in xs
            ]
        )
        # Placeholder: use Wigner profile along x as the x-marginal proxy
        W = np.array([wigner_fock(state, float(x), 0.0) for x in xs])
        n, sp, ct = comb_score(np.abs(W) + 1e-12)
        print(f"  r={r:.1f}: outcome m_x={results['m_x']:.2f} "
              f"peaks={n} spacing={sp if n>1 else float('nan'):.2f} contrast={ct:.2f}")


if __name__ == "__main__":
    main()
