"""Final user acceptance: U1–U5 + U7 + U8 + U9. Run all, then summary; exit 1 if any fail."""

from __future__ import annotations

import sys
from collections.abc import Callable

import numpy as np

from cvsim.bosonic import (
    BosonicState,
    even_cat,
    gkp0,
    homodyne_condition as b_cond,
    homodyne_sample as b_sample,
    loss as b_loss,
    mean_photon as b_n,
    phase as b_phase,
    weight_sum,
)
from cvsim.fock import FockState, beamsplitter as f_bs, loss as f_loss, mean_photon as f_n, norm, squeeze as f_squeeze, trace as f_trace
from cvsim.fock.density import FockDensity
from cvsim.fock.gates import displace as f_displace
from cvsim.fock.gates import squeeze as f_squeeze_gate
from cvsim.gaussian import (
    GaussianState,
    beamsplitter,
    det_cov,
    displace,
    homodyne_condition,
    homodyne_mean,
    homodyne_sample as g_sample,
    homodyne_sample_and_condition,
    homodyne_var,
    loss as g_loss,
    mean_photon,
    phase,
    squeeze,
)
from cvsim.wigner import wigner_fock

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


def _u7() -> tuple[bool, str]:
    """Extended smoke: G loss/condition, F BS, B gkp0/loss."""
    alpha, T = 0.7 + 0.2j, 0.4
    g_ok = abs(mean_photon(g_loss(displace(GaussianState.vacuum(1), alpha), T)) - T * abs(alpha) ** 2) < 1e-12

    st_c = homodyne_condition(GaussianState.vacuum(1), 0, 0.0, 0.25)
    c_ok = abs(st_c.V[0, 0]) < 1e-12 and abs(st_c.rbar[0] - 0.25) < 1e-12

    st_f = f_bs(FockState.fock2(1, 0, 12), np.pi / 4)
    f_ok = abs(abs(st_f.amps[1, 0]) ** 2 - 0.5) < 1e-6 and abs(abs(st_f.amps[0, 1]) ** 2 - 0.5) < 1e-6

    st_g = gkp0(0.1, grid_size=3)
    xs = sorted(float(c.rbar[0].real) for c in st_g.components)
    delta = np.sqrt(2.0 * np.pi)
    gkp_ok = (
        st_g.n_components == 7
        and abs(weight_sum(st_g) - 1.0) < 1e-12
        and abs((xs[1] - xs[0]) - delta) < 1e-12
    )

    st_bl = b_loss(even_cat(0.8), 0.0)
    b_ok = abs(b_n(st_bl)) < 1e-12 and abs(weight_sum(st_bl) - 1.0) < 1e-12

    ok = g_ok and c_ok and f_ok and gkp_ok and b_ok
    return ok, f"G_loss={g_ok} cond={c_ok} F_BS={f_ok} gkp0={gkp_ok} B_loss={b_ok}"


def _u8() -> tuple[bool, str]:
    """Queue ①②③ smoke: B condition, Homodyne sample G/B, Fock loss."""
    alpha = 0.8
    st2 = b_cond(even_cat(alpha), 0, 0.0, np.sqrt(2.0) * alpha)
    b_cond_ok = (
        st2.n_components == 4
        and abs(weight_sum(st2) - 1.0) < 1e-10
        and abs(st2.components[0].w) > abs(st2.components[1].w)
    )

    rng = np.random.default_rng(0)
    xs = np.array([g_sample(GaussianState.vacuum(1), rng=rng) for _ in range(2000)])
    g_samp_ok = abs(xs.mean()) < 0.08 and abs(xs.var(ddof=1) - 0.5) < 0.08

    st_g = squeeze(GaussianState.vacuum(1), 0.4)
    o_g = g_sample(st_g, rng=np.random.default_rng(7))
    o_b = b_sample(BosonicState.from_gaussian(st_g), rng=np.random.default_rng(7))
    gb_ok = abs(o_g - o_b) < 1e-12

    T = 0.3
    rho = f_loss(FockState.fock(1, 8), T)
    f_ok = (
        abs(rho.rho[0, 0] - (1.0 - T)) < 1e-12
        and abs(rho.rho[1, 1] - T) < 1e-12
        and abs(f_trace(rho) - 1.0) < 1e-12
    )

    ok = b_cond_ok and g_samp_ok and gb_ok and f_ok
    return ok, f"B_cond={b_cond_ok} G_samp={g_samp_ok} GB={gb_ok} F_loss={f_ok}"


def _u9() -> tuple[bool, str]:
    """P0 gap-fill smoke: Fock Wigner, density gate, sample_and_condition."""
    w_vac = wigner_fock(FockState.vacuum(8), 0.0, 0.0)
    w1 = wigner_fock(FockState.fock(1, 8), 0.0, 0.0)
    w_ok = abs(w_vac - 1.0 / np.pi) < 1e-12 and w1 < -1e-3

    rho = f_loss(FockState.fock(1, 12), 0.4)
    rho2 = f_displace(rho, 0.3)
    dens_ok = abs(f_trace(rho2) - 1.0) < 1e-10

    o, st = homodyne_sample_and_condition(
        GaussianState.vacuum(1), rng=np.random.default_rng(1)
    )
    sc_ok = abs(st.V[0, 0]) < 1e-12 and abs(st.rbar[0] - o) < 1e-12

    ok = w_ok and dens_ok and sc_ok
    return ok, f"W={w_ok} dens={dens_ok} sc={sc_ok}"


def main() -> int:
    checks: list[tuple[str, CheckFn]] = [
        ("U1 vacuum/conventions", _u1),
        ("U2 squeeze+homodyne var", _u2),
        ("U3 D/BS/phase circuit", _u3),
        ("U4 Fock cutoff", _u4),
        ("U5 cat weights+phase", _u5),
        ("U7 extended G/F/B smoke", _u7),
        ("U8 queue ①②③ smoke", _u8),
        ("U9 P0 gap-fill smoke", _u9),
    ]
    results: list[tuple[str, bool, str]] = []
    print("cvsim user acceptance (U1–U5 + U7–U9); run-all then summary")
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
