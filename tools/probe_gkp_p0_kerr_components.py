"""Phase 0 probe: can we approximate kerr(|alpha>) using a finite sum of
coherent-state components (bosonic component representation)?

Physics: e^{i chi n^2} |alpha>. The Kerr phase depends on n^2. For the
"Kerr echo" one can expand the Fock amplitudes and compare against a finite
superposition of coherent states. We test whether a q-coherent-state sum can
approach the exact (truncated) Fock kerr state, scoring fidelity.

Method (clean):
  target[n] = e^{i chi n^2} <n|alpha>          (exact kerr in Fock basis)
  ansatz    = sum_k c_k <n|alpha_k>            (q coherent components)
  Solve c_k by least squares with target up to cutoff; report |<t|a>|^2/(...).
"""

from __future__ import annotations

import warnings
from math import factorial

import numpy as np

warnings.filterwarnings("ignore")


def coherent_amp(alpha: complex, n: int) -> float:
    """<n|alpha> = e^{-|a|^2/2} a^n / sqrt(n!)  (scalar n)."""
    return float(np.exp(-0.5 * abs(alpha) ** 2) * alpha**n / float(factorial(n)) ** 0.5)


def target_amps(alpha: complex, chi: float, cutoff: int) -> np.ndarray:
    n = np.arange(cutoff)
    cn = np.array([coherent_amp(alpha, int(k)) for k in n], dtype=complex)
    return np.exp(1j * chi * n * n) * cn


def basis_matrix(alphas: list[complex], cutoff: int) -> np.ndarray:
    return np.array(
        [[coherent_amp(ak, n) for ak in alphas] for n in range(cutoff)],
        dtype=complex,
    )


def fidelity_approx(target: np.ndarray, alphas: list[complex]) -> tuple[float, np.ndarray]:
    cutoff = len(target)
    M = basis_matrix(alphas, cutoff)
    c, *_ = np.linalg.lstsq(M, target, rcond=None)
    approx = M @ np.asarray(c)
    num = abs(np.vdot(target, approx)) ** 2
    denom = (np.vdot(target, target).real) * (np.vdot(approx, approx).real)
    fid = float(num / denom) if denom else 0.0
    return fid, np.asarray(c)


def main() -> None:
    cutoff = 40
    print("=" * 74)
    print("Phase 0 probe: kerr(|alpha>) ~ coherent-state components")
    print("   fidelity = |<target | approx_coherent_sum>|^2  (cutoff=%d)" % cutoff)
    print("=" * 74)
    for alpha in (1.5, 2.0):
        for chi in (np.pi / 2, np.pi / 4, np.pi / 8, 0.3, 0.7):
            target = target_amps(complex(alpha), float(chi), cutoff)
            row = []
            for q in (2, 4, 6, 8, 12, 16):
                alphas = [abs(alpha) * np.exp(2j * np.pi * k / q) for k in range(q)]
                fid, _ = fidelity_approx(target, alphas)
                row.append(f"{q}:{fid:.4f}")
            print(f"  alpha={alpha:.1f} chi={chi:.3f} -> " + "  ".join(row))


if __name__ == "__main__":
    main()
