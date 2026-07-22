"""M4: same physics across G / F / B (T4–T7)."""

from __future__ import annotations

import numpy as np

from cvsim.bosonic import BosonicState
from cvsim.bosonic import loss as b_loss
from cvsim.bosonic import mean_photon as b_n
from cvsim.fock import FockState
from cvsim.fock import displace as f_displace
from cvsim.fock import homodyne_mean as f_hmean
from cvsim.fock import loss as f_loss
from cvsim.fock import mean_photon as f_n
from cvsim.fock import squeeze as f_squeeze
from cvsim.fock import two_mode_squeeze as f_tms
from cvsim.gaussian import GaussianState
from cvsim.gaussian import displace as g_displace
from cvsim.gaussian import homodyne_mean as g_hmean
from cvsim.gaussian import loss as g_loss
from cvsim.gaussian import mean_photon as g_n
from cvsim.gaussian import squeeze as g_squeeze
from cvsim.gaussian import two_mode_squeeze as g_tms


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


def t5_s2_n(r: float = 0.3, fock_cutoff: int = 24) -> None:
    n_ex = float(np.sinh(r) ** 2)
    st_g = g_tms(GaussianState.vacuum(2), r, 0, 1)
    st_f = f_tms(FockState.vacuum(fock_cutoff, nmode=2), r)
    n_g0, n_g1 = g_n(st_g, 0), g_n(st_g, 1)
    n_f0, n_f1 = f_n(st_f, 0), f_n(st_f, 1)
    print(f"T5 S2 <n>  r={r}  cutoff={fock_cutoff}")
    print(
        f"  analytic={n_ex:.10f}  "
        f"G=({n_g0:.10f},{n_g1:.10f})  F=({n_f0:.10f},{n_f1:.10f})"
    )
    assert abs(n_g0 - n_ex) < 1e-12 and abs(n_g1 - n_ex) < 1e-12
    assert abs(n_f0 - n_ex) < 5e-3 and abs(n_f1 - n_ex) < 5e-3
    assert abs(n_f0 - n_g0) < 1e-2 and abs(n_f1 - n_g1) < 1e-2


def t6_thermal_n(nbar: float = 0.5, T: float = 0.0) -> None:
    st_g = g_loss(GaussianState.vacuum(1), T, nbar=nbar)
    st_b = b_loss(BosonicState.vacuum(1), T, nbar=nbar)
    n_g, n_b = g_n(st_g), b_n(st_b)
    print(f"T6 thermal loss  T={T}  nbar={nbar}")
    print(f"  expect={nbar:.10f}  G={n_g:.10f}  B={n_b:.10f}")
    assert abs(n_g - nbar) < 1e-12, f"G <n>={n_g} != {nbar}"
    assert abs(n_b - n_g) < 1e-12, f"B <n>={n_b} != G {n_g}"


def t7_homodyne_mean(
    alpha: complex = 0.55 + 0.2j,
    fock_cutoff: int = 28,
) -> None:
    st_g = g_displace(GaussianState.vacuum(1), alpha)
    st_f = f_displace(FockState.vacuum(fock_cutoff), alpha)
    print(f"T7 Homodyne mean  alpha={alpha}  cutoff={fock_cutoff}")
    for phi in (0.0, 0.25 * np.pi, 0.5 * np.pi):
        mg = g_hmean(st_g, 0, phi)
        mf = f_hmean(st_f, 0, phi)
        print(f"  phi={phi:.3f}  G={mg:.10f}  F={mf:.10f}")
        assert abs(mg - mf) < 1e-6, f"phi={phi}: G={mg} F={mf}"


def main() -> None:
    print("M4 cross-rep (G / F / B where comparable)")
    t4_squeeze_n()
    t1_coherent_loss()
    t5_s2_n()
    t6_thermal_n()
    t7_homodyne_mean()
    print("OK: T4 + T1 + T5 + T6 + T7 passed")


if __name__ == "__main__":
    main()
