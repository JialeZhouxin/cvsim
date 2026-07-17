"""M2 AC: same squeeze as M1; cutoff scan → ⟨n⟩ → sinh²r; truncation error visible."""

from __future__ import annotations

import numpy as np

from cvsim.fock import FockState, mean_photon, norm, squeeze
from cvsim.fock.gates import squeeze as squeeze_gate

R = 0.5
N_EXACT = float(np.sinh(R) ** 2)
CUTOFFS = [4, 6, 8, 12, 20]


def project_to_cutoff(amps: np.ndarray, cutoff: int) -> FockState:
    """Keep first `cutoff` amplitudes (truncation of a richer state)."""
    return FockState(amps=amps[:cutoff].copy())


def main() -> None:
    print(f"M2 Fock cutoff scan  r={R}  sinh^2(r)={N_EXACT:.6f}")
    errs = []
    for N in CUTOFFS:
        st = squeeze(FockState.vacuum(N), r=R)
        n = mean_photon(st)
        nm = norm(st)
        err = abs(n - N_EXACT)
        errs.append(err)
        print(f"  cutoff={N:3d}  <n>={n:.6f}  |err|={err:.3e}  norm(U_trunc)={nm:.6f}")

    # AC2.1
    assert errs[-1] < 1e-3, f"large cutoff still bad: err={errs[-1]}"

    # AC2.2: larger cutoff closer to analytic
    assert errs[-1] < errs[0], f"error not improved: {errs[0]} → {errs[-1]}"
    assert errs[-1] / max(N_EXACT, 1e-12) < 1e-3

    # AC2.3: true truncation deficit — evolve at high cutoff, then chop to low N
    # (truncated unitary alone preserves ‖ψ‖; projecting infinite/high space does not)
    rich = squeeze_gate(FockState.vacuum(40), r=R)
    low = project_to_cutoff(rich.amps, 4)
    deficit = 1.0 - norm(low)
    print(f"  project N=40→4: retained prob={norm(low):.6f}  deficit={deficit:.3e}")
    assert deficit > 1e-4, f"expected visible truncation deficit, got {deficit}"

    print("OK: AC2.1–2.3 passed")


if __name__ == "__main__":
    main()
