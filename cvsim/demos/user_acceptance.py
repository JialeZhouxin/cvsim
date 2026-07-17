"""Final user acceptance: U1–U5. Run all, then summary; exit 1 if any fail."""

from __future__ import annotations

import sys
from collections.abc import Callable

import numpy as np

from cvsim.bosonic import even_cat, phase as b_phase, weight_sum
from cvsim.fock import FockState, mean_photon as f_n, norm, squeeze as f_squeeze
from cvsim.fock.gates import squeeze as f_squeeze_gate
from cvsim.gaussian import (
    GaussianState,
    beamsplitter,
    det_cov,
    displace,
    homodyne_mean,
    homodyne_var,
    mean_photon,
    phase,
    squeeze,
)

CheckFn = Callable[[], tuple[bool, str]]


def _u1() -> tuple[bool, str]:
    st = GaussianState.vacuum(1)
    ok = (
        np.allclose(st.rbar, 0.0)
        and np.allclose(st.V, 0.5 * np.eye(2))
        and abs(det_cov(st) - 0.25) < 1e-12
    )
    return ok, f"detV={det_cov(st):.6g}"


def _u2() -> tuple[bool, str]:
    r = 0.8
    st = squeeze(GaussianState.vacuum(1), r=r)
    n_ex = float(np.sinh(r) ** 2)
    ok = (
        abs(det_cov(st) - 0.25) < 1e-10
        and abs(mean_photon(st) - n_ex) < 1e-10
        and abs(homodyne_var(st, 0, 0.0) - 0.5 * np.exp(-2 * r)) < 1e-10
        and abs(homodyne_var(st, 0, np.pi / 2) - 0.5 * np.exp(2 * r)) < 1e-10
    )
    return ok, f"<n>={mean_photon(st):.6g} expect={n_ex:.6g}"


def _u3() -> tuple[bool, str]:
    alpha = 0.4 + 0.25j
    st_d = displace(GaussianState.vacuum(1), alpha)
    mean_ok = abs(mean_photon(st_d) - abs(alpha) ** 2) < 1e-12
    phi = 0.5
    expect_m = np.sqrt(2) * (alpha.real * np.cos(phi) + alpha.imag * np.sin(phi))
    mean_h_ok = abs(homodyne_mean(st_d, 0, phi) - expect_m) < 1e-12

    r = 0.5
    st = beamsplitter(squeeze(GaussianState.vacuum(2), r=r, mode=0), 0, 1, np.pi / 4)
    bs_ok = (
        abs(mean_photon(st) - np.sinh(r) ** 2) < 1e-12
        and abs(det_cov(st) - 0.25**2) < 1e-10
    )

    r2, th = 0.7, 0.35
    st_p = phase(squeeze(GaussianState.vacuum(1), r2), th)
    c, s = 1.0, 0.0  # phi=0
    V = st_p.V
    expect_v = c * c * V[0, 0] + s * s * V[1, 1] + 2 * s * c * V[0, 1]
    phase_ok = (
        abs(homodyne_var(st_p, 0, 0.0) - expect_v) < 1e-12
        and abs(homodyne_var(st_p, 0, 0.0) - 0.5 * np.exp(-2 * r2)) > 1e-6
    )
    ok = mean_ok and mean_h_ok and bs_ok and phase_ok
    return ok, f"D/BS/phase checks mean_ok={mean_ok} bs_ok={bs_ok} phase_ok={phase_ok}"


def _u4() -> tuple[bool, str]:
    r = 0.5
    n_ex = float(np.sinh(r) ** 2)
    cutoffs = [4, 6, 8, 12, 20]
    errs = [abs(f_n(f_squeeze(FockState.vacuum(N), r)) - n_ex) for N in cutoffs]
    rich = f_squeeze_gate(FockState.vacuum(40), r)
    low = FockState(amps=rich.amps[:4].copy())
    deficit = 1.0 - norm(low)
    ok = errs[-1] < 1e-3 and errs[-1] < errs[0] and deficit > 1e-4
    return ok, f"err_hi={errs[-1]:.3e} deficit40→4={deficit:.3e}"


def _u5() -> tuple[bool, str]:
    st = even_cat(0.8)
    s0 = weight_sum(st)
    th = 0.5
    st2 = b_phase(st, th)
    r0 = st.components[0].rbar
    r0p = st2.components[0].rbar
    c, s = np.cos(th), np.sin(th)
    expect = np.array([c * r0[0] - s * r0[1], s * r0[0] + c * r0[1]])
    ok = (
        st.n_components == 4
        and abs(s0 - 1.0) < 1e-12
        and abs(weight_sum(st2) - 1.0) < 1e-12
        and np.allclose(r0p, expect, atol=1e-12)
    )
    return ok, f"K={st.n_components} sum_w={s0:.6g}"


def main() -> int:
    checks: list[tuple[str, CheckFn]] = [
        ("U1 vacuum/conventions", _u1),
        ("U2 squeeze+homodyne var", _u2),
        ("U3 D/BS/phase circuit", _u3),
        ("U4 Fock cutoff", _u4),
        ("U5 cat weights+phase", _u5),
    ]
    results: list[tuple[str, bool, str]] = []
    print("cvsim user acceptance (U1–U5); run-all then summary")
    for name, fn in checks:
        try:
            ok, detail = fn()
        except Exception as e:  # keep going (summary policy)
            ok, detail = False, f"EXC {type(e).__name__}: {e}"
        results.append((name, ok, detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}  {detail}")

    n_fail = sum(0 if ok else 1 for _, ok, _ in results)
    print("---")
    print(f"summary: {len(results) - n_fail}/{len(results)} PASS, {n_fail} FAIL")
    if n_fail:
        print("USER_ACCEPTANCE: FAIL")
        return 1
    print("USER_ACCEPTANCE: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
