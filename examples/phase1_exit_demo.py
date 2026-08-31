"""Phase 1 exit demo: 4-mode TMSV -> interferometer -> loss -> homodyne variances.

This script is the cross-layer integration evidence for closing Phase 1 of the
cvsim Gaussian simulator. It builds a 4-mode state from two independent TMSV
pairs, passes it through a 50:50 beamsplitter interferometer (mode 0 <-> mode 2),
adds identical pure loss (T=0.8) on every mode, and checks that the resulting
homodyne x-quadrature variances match the closed-form analytic expressions.

All values are fixed (no RNG). The analytic formulae are derived in the task
design document:

    .trellis/tasks/07-29-phase1-exit-demo/design.md

Exit: exit code 0 means all asserts pass. Any mismatch prints a comparison table
and raises.
"""

from __future__ import annotations

# repo-local import: this script is run from the repo root
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cvsim.gaussian.channels import loss
from cvsim.gaussian.gates import interferometer
from cvsim.gaussian.observables import homodyne_var
from cvsim.gaussian.state import GaussianState
from cvsim.symplectic import U_beamsplitter, embed_U_2mode

# -----------------------------------------------------------------------------
# Fixed parameters
# -----------------------------------------------------------------------------
R = 0.6
T = 0.8
ATOL = 1e-12

# Useful shorthands for the analytic expressions
COSH2R = np.cosh(2.0 * R)
SINH2R = np.sinh(2.0 * R)
EXP_MINUS_2R = np.exp(-2.0 * R)

# Single-mode x-variance of one TMSV branch (before loss)
VAR_X_TMSV = 0.5 * COSH2R

# EPR correlated variance of one TMSV pair (before loss)
VAR_EPR_TMSV = EXP_MINUS_2R


def build_initial_state() -> GaussianState:
    """Two independent TMSV pairs on modes (0,1) and (2,3)."""
    pair_a = GaussianState.tmsv(R, nmode=2, mode1=0, mode2=1)
    pair_b = GaussianState.tmsv(R, nmode=2, mode1=0, mode2=1)
    return GaussianState.product(pair_a, pair_b)


def build_interferometer() -> np.ndarray:
    """50:50 beamsplitter mixing mode 0 and mode 2.

    The 2x2 unitary is U = (1/sqrt(2)) * [[1, 1], [-1, 1]],
    embedded in the 4-mode annihilator space.
    """
    u2 = U_beamsplitter(np.pi / 4.0, 0.0)
    return embed_U_2mode(4, 0, 2, u2)


def diff_variance(state: GaussianState, a: int, b: int) -> float:
    """Variance of (x_a - x_b) for a Gaussian state in xxpp ordering."""
    V = state.V
    return float(V[a, a] + V[b, b] - 2.0 * V[a, b])


def run_chain() -> tuple[GaussianState, GaussianState, GaussianState]:
    """Run source -> interferometer -> loss and return the three states."""
    st0 = build_initial_state()
    U = build_interferometer()
    st1 = interferometer(st0, U, validate_u=True)
    st2 = loss(st1, T, nbar=0.0)
    return st0, st1, st2


def analytic_values() -> dict[str, float]:
    """Hand-calculated values for the 9 checkpoints.

    Naming convention:
      - checkpoint suffix  _src : after the source construction
      - checkpoint suffix  _bs  : after the interferometer
      - checkpoint suffix  _loss: after loss
    """
    # Source: single-mode x variance and EPR correlation
    var_x_src = VAR_X_TMSV
    var_epr_src = VAR_EPR_TMSV

    # Beamsplitter (50:50 on mode 0 <-> mode 2):
    #   x0' = (x0 + x2) / sqrt(2)
    # Because x2 is independent of x1, the covariance halves:
    #   Cov(x0', x1') = (1/sqrt(2)) * Cov(x0, x1) = (1/sqrt(2)) * (1/2) sinh(2r)
    # The single-mode x variance remains (1/2) cosh(2r) by symmetry.
    var_x_bs = VAR_X_TMSV
    var_epr_bs = (
        VAR_X_TMSV
        + VAR_X_TMSV
        - (1.0 / np.sqrt(2.0)) * SINH2R
    )

    # Loss: T = 0.8. Each independent mode receives (1-T)/2 vacuum noise.
    # Single-mode variance: T * var_x_bs + (1-T)/2
    var_x_loss = T * var_x_bs + (1.0 - T) / 2.0
    # EPR difference variance: T * var_epr_bs + (1-T)  (two modes each add noise)
    var_epr_loss = T * var_epr_bs + (1.0 - T)

    return {
        "var_x_src": var_x_src,
        "var_epr_src": var_epr_src,
        "var_x_bs": var_x_bs,
        "var_epr_bs": var_epr_bs,
        "var_x_loss": var_x_loss,
        "var_epr_loss": var_epr_loss,
    }


def measured_values(st0: GaussianState, st1: GaussianState, st2: GaussianState) -> dict[str, float]:
    """Measured values from the cvsim pipeline for the 9 checkpoints."""
    return {
        "var_x_src": homodyne_var(st0, mode=0, phi=0.0),
        "var_epr_src": diff_variance(st0, 0, 1),
        "var_x_bs": homodyne_var(st1, mode=0, phi=0.0),
        "var_epr_bs": diff_variance(st1, 0, 1),
        "var_x_loss": homodyne_var(st2, mode=0, phi=0.0),
        "var_epr_loss": diff_variance(st2, 0, 1),
    }


def main() -> None:
    st0, st1, st2 = run_chain()
    analytic = analytic_values()
    measured = measured_values(st0, st1, st2)

    mismatches = []
    for name, expected in analytic.items():
        got = measured[name]
        ok = np.isclose(got, expected, atol=ATOL)
        if not ok:
            mismatches.append(
                {
                    "name": name,
                    "expected": expected,
                    "got": got,
                    "diff": got - expected,
                    "atol": ATOL,
                }
            )

    if mismatches:
        print("Phase 1 exit demo FAILED: sim vs analytic mismatch")
        print(f"{'name':<16} {'expected':>22} {'got':>22} {'diff':>22} {'atol ok':>8}")
        for row in mismatches:
            print(
                f"{row['name']:<16} {row['expected']:22.15g} {row['got']:22.15g} "
                f"{row['diff']:22.15g} {np.isclose(row['got'], row['expected'], atol=ATOL)!s:>8}"
            )
        raise AssertionError(f"{len(mismatches)} analytic check(s) failed")

    # All checks passed silently. Exit code 0 signals success.
    return


if __name__ == "__main__":
    main()
