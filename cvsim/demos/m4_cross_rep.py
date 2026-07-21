"""M4: same physics across G / F / B (T4 squeeze ⟨n⟩, T1 coherent+loss)."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic import BosonicState
from cvsim.bosonic import loss as b_loss
from cvsim.bosonic import mean_photon as b_n
from cvsim.fock import FockState
from cvsim.fock import displace as f_displace
from cvsim.fock import loss as f_loss
from cvsim.fock import mean_photon as f_n
from cvsim.fock import squeeze as f_squeeze
from cvsim.gaussian import GaussianState
from cvsim.gaussian import displace as g_displace
from cvsim.gaussian import loss as g_loss
from cvsim.gaussian import mean_photon as g_n
from cvsim.gaussian import squeeze as g_squeeze


def t4_squeeze_n(r: float = 0.5, fock_cutoff: int = 24) -> None:
    n_ex = float(np.sinh(r) ** 2)
    n_g = g_n(g_squeeze(GaussianState.vacuum(1), r))
    n_f = f_n(f_squeeze(FockState.vacuum(fock_cutoff), r))
    print(f"T4 squeeze <n>  r={r}  cutoff={fock_cutoff}")
    print(f"  analytic={n_ex:.10f}  G={n_g:.10f}  F={n_f:.10f}")
    assert abs(n_g - n_ex) < 1e-12, f"G <n>={n_g} != {n_ex}"
    assert abs(n_f - n_ex) < 1e-3, f"F <n>={n_f} vs analytic {n_ex}"


def t1_coherent_loss(
    alpha: complex = 0.7,
    T: float = 0.4,
    fock_cutoff: int = 24,
) -> None:
    n_ex = T * abs(alpha) ** 2
    g_coh = g_displace(GaussianState.vacuum(1), alpha)
    n_g = g_n(g_loss(g_coh, T))
    n_f = f_n(f_loss(f_displace(FockState.vacuum(fock_cutoff), alpha), T))
    n_b = b_n(b_loss(BosonicState.from_gaussian(g_coh), T))
    print(f"T1 coherent+loss  alpha={alpha}  T={T}  cutoff={fock_cutoff}")
    print(
        f"  analytic={n_ex:.10f}  G={n_g:.10f}  F={n_f:.10f}  B={n_b:.10f}"
    )
    assert abs(n_g - n_ex) < 1e-12, f"G <n>={n_g} != {n_ex}"
    assert abs(n_b - n_g) < 1e-12, f"B <n>={n_b} != G {n_g}"
    assert abs(n_f - n_ex) < 0.05, f"F <n>={n_f} vs analytic {n_ex}"


def main() -> None:
    print("M4 cross-rep (G / F / B where comparable)")
    t4_squeeze_n()
    t1_coherent_loss()
    print("OK: T4 + T1 passed")


if __name__ == "__main__":
    main()
