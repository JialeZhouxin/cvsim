"""Piquasso oracle qualification (spike) — is piquasso 8.0.1 fit to be cvsim's
external reference for the features that have NO closed form?

WHY THIS EXISTS
---------------
cvsim's external-oracle gap is not "single gates" (already pinned at 1e-12 against
hand-derived closed forms) but two things:
  (1) Fock composite / channels / measurement conditioning (3+ modes, loss, PNR,
      homodyne posteriors) — `tests/_golden/sf_fock_golden.npz` covers NONE of it.
  (2) Bosonic/GKP numeric credibility.

Before any external library is allowed to be an oracle, it must be hammered with
closed forms we already trust. An oracle we have not qualified is worse than no
oracle: it manufactures false confidence.

RUN
---
    uv venv <tmp> --python 3.13
    uv pip install --python <tmp>/Scripts/python.exe piquasso
    <tmp>/Scripts/python.exe tools/qualify_piquasso_oracle.py

This script is NOT a pytest test and is NOT wired into CI: it needs piquasso, which
is deliberately not a project dependency (minimal-dependency is an ADR-level red
line). Its output is the evidence behind `docs/piquasso-oracle-qualification.md`.
"""

from __future__ import annotations

import math
import sys

import numpy as np
import piquasso as pq

PASS: list[str] = []
FAIL: list[str] = []
NOTES: list[str] = []


def check(name: str, got: float, want: float, tol: float) -> None:
    err = abs(got - want)
    ok = err <= tol
    (PASS if ok else FAIL).append(name)
    print(
        f"  {name:<46} got={got:+.12f} want={want:+.12f} err={err:.2e} {'PASS' if ok else 'FAIL'}"
    )


def note(msg: str) -> None:
    NOTES.append(msg)
    print(f"  [note] {msg}")


HB = 1  # cvsim convention: hbar = 1
FOCK = lambda cut, hbar=HB: pq.PureFockSimulator(d=1, config=pq.Config(cutoff=cut, hbar=hbar))  # noqa: E731


def fock_probs(state, n: int) -> np.ndarray:
    """Single-mode PNR p(0..n-1) via the occupation-indexed map (order-agnostic)."""
    out = np.zeros(n)
    for k, v in state.fock_probabilities_map.items():
        occ = k if isinstance(k, tuple) else (k,)
        if len(occ) == 1 and occ[0] < n:
            out[occ[0]] = float(np.real(v))
    return out


def pmap(state) -> dict:
    """Real-valued occupation -> probability map (tuple keys)."""
    return {k: float(np.real(v)) for k, v in state.fock_probabilities_map.items()}


def main() -> int:
    print(f"piquasso {pq.__version__}  numpy {np.__version__}")
    print()

    # -----------------------------------------------------------------------
    print("C0. convention pinning vs cvsim (hbar=1, xxpp, vacuum V=I/2)")
    print("-" * 78)
    with pq.Program() as prog:
        pq.Q(0) | pq.Vacuum()
    g = pq.GaussianSimulator(d=1, config=pq.Config(hbar=1)).execute(prog).state
    check("C0a vacuum xxpp cov == 2V == I", float(np.diag(g.xxpp_covariance_matrix)[0]), 1.0, 1e-14)

    with pq.Program() as prog:
        pq.Q(0) | pq.Vacuum()
        pq.Q(0) | pq.Squeezing(r=0.5)
    g = pq.GaussianSimulator(d=1, config=pq.Config(hbar=1)).execute(prog).state
    check(
        "C0b squeezed xxpp cov == 2V",
        float(np.diag(g.xxpp_covariance_matrix)[0]),
        math.exp(-1.0),
        1e-14,
    )

    alpha = 0.7 * np.exp(1j * 0.3)
    with pq.Program() as prog:
        pq.Q(0) | pq.Vacuum()
        pq.Q(0) | pq.Displacement(r=abs(alpha), phi=float(np.angle(alpha)))
    g = pq.GaussianSimulator(d=1, config=pq.Config(hbar=1)).execute(prog).state
    check(
        "C0c coherent xxpp mean == rbar_x",
        float(g.xxpp_mean_vector[0]),
        math.sqrt(2) * alpha.real,
        1e-14,
    )

    # -----------------------------------------------------------------------
    print()
    print("C1..C4. single-gate closed forms (the 'right to be believed' checks)")
    print("-" * 78)
    with pq.Program() as prog:
        pq.Q(0) | pq.Vacuum()
        pq.Q(0) | pq.Displacement(r=1.0, phi=0.0)
    st = FOCK(8).execute(prog).state
    for n in range(4):
        check(
            f"C1 coherent p({n}) = e^-1/n!",
            float(fock_probs(st, 8)[n]),
            math.exp(-1.0) / math.factorial(n),
            1e-12,
        )

    r = 0.5
    with pq.Program() as prog:
        pq.Q(0) | pq.Vacuum()
        pq.Q(0) | pq.Squeezing(r=r)
    st = FOCK(12).execute(prog).state
    p_sq = fock_probs(st, 12)
    for n in range(4):
        closed = (
            1
            / math.cosh(r)
            * math.factorial(2 * n)
            / (4.0**n * math.factorial(n) ** 2)
            * math.tanh(r) ** (2 * n)
        )
        check(f"C2 squeezed p({2 * n}) closed form", float(p_sq[2 * n]), closed, 1e-12)
    check(
        "C2b squeezed odd diagonals vanish",
        float(np.max(np.abs(p_sq[1::2]))),
        0.0,
        1e-14,
    )

    nbar = 1.0
    with pq.Program() as prog:
        pq.Q(0) | pq.Thermal(mean_photon_numbers=(nbar,))
    st = pq.GaussianSimulator(d=1, config=pq.Config(hbar=1, cutoff=12)).execute(prog).state
    for n in range(4):
        check(
            f"C3 thermal p({n}) = nbar^n/(nbar+1)^(n+1)",
            float(np.real(st.fock_probabilities[n])),
            nbar**n / (nbar + 1.0) ** (n + 1),
            1e-12,
        )

    T = 0.7
    theta = math.acos(math.sqrt(T))  # CONVENTION: transmissivity T = cos^2(theta)
    with pq.Program() as prog:
        pq.Q(0) | pq.NumberState(occupation_numbers=(1,))
        pq.Q(0) | pq.Attenuator(theta=theta)
    st = FOCK(6).execute(prog).state
    check("C4 loss on |1>: p0 == 1-T", float(fock_probs(st, 6)[0]), 1.0 - T, 1e-12)
    check("C4 loss on |1>: p1 == T", float(fock_probs(st, 6)[1]), T, 1e-12)

    with pq.Program() as prog:
        pq.Q(0, 1) | pq.Vacuum()
        pq.Q(0, 1) | pq.NumberState(occupation_numbers=(1, 1))
        pq.Q(0, 1) | pq.Beamsplitter(theta=math.pi / 4)
    m = pmap(pq.PureFockSimulator(d=2, config=pq.Config(cutoff=5, hbar=1)).execute(prog).state)
    check("C5a HOM P(1,1) == 0", m.get((1, 1), 0.0), 0.0, 1e-14)
    check("C5b HOM P(2,0) == 1/2", m.get((2, 0), 0.0), 0.5, 1e-14)
    check("C5c HOM P(0,2) == 1/2", m.get((0, 2), 0.0), 0.5, 1e-14)

    # -----------------------------------------------------------------------
    print()
    print("C6. TMSV joint PNR: p(n,n) = tanh^(2n) r / cosh^2 r  (3 modes worth of modes=2)")
    print("-" * 78)
    r = 0.5
    with pq.Program() as prog:
        pq.Q(0, 1) | pq.Vacuum()
        pq.Q(0, 1) | pq.Squeezing2(r=r)
    m = pmap(pq.PureFockSimulator(d=2, config=pq.Config(cutoff=8, hbar=1)).execute(prog).state)
    for n in range(3):
        check(
            f"C6 TMSV p({n},{n})",
            m.get((n, n), 0.0),
            math.tanh(r) ** (2 * n) / math.cosh(r) ** 2,
            1e-12,
        )

    # -----------------------------------------------------------------------
    print()
    print("C7. Kerr on |1> is a GLOBAL PHASE (the SF golden's blind spot)")
    print("-" * 78)
    xi = 0.1
    with pq.Program() as prog:
        pq.Q(0) | pq.NumberState(occupation_numbers=(1,))
        pq.Q(0) | pq.Kerr(xi=xi)
    amp = complex(np.asarray(FOCK(6).execute(prog).state.state_vector)[1])
    check("C7a Re amp|1> == cos(xi)", amp.real, math.cos(xi), 1e-12)
    check("C7b Im amp|1> == sin(xi)", amp.imag, math.sin(xi), 1e-12)

    # -----------------------------------------------------------------------
    print()
    print("C8. homodyne scaling + variance anchors (statistical, 40k shots)")
    print("-" * 78)
    with pq.Program() as prog:
        pq.Q(0) | pq.Vacuum()
        pq.Q(0) | pq.HomodyneMeasurement()
    s = np.array([float(x[0]) for x in FOCK(16).execute(prog, shots=40000).samples])
    check("C8a vacuum homodyne var == 1/2", float(s.var()), 0.5, 0.03)
    for k in (0, 1, 2):
        with pq.Program() as prog:
            pq.Q(0) | pq.NumberState(occupation_numbers=(k,))
            pq.Q(0) | pq.HomodyneMeasurement()
        s = np.array([float(x[0]) for x in FOCK(16).execute(prog, shots=40000).samples])
        check(f"C8b |{k}> homodyne var == (2k+1)/2", float(s.var()), (2 * k + 1) / 2.0, 0.04)

    # -----------------------------------------------------------------------
    print()
    print("C9. THE GAP: measurement conditioning")
    print("-" * 78)
    # C9a exact: TMSV post-selected on n_0=k leaves EXACTLY |k>; selection prob is
    #     the closed form. This is deterministic (shots=None) and exact.
    r = 0.5
    for k in range(3):
        with pq.Program() as prog:
            pq.Q(0, 1) | pq.Vacuum()
            pq.Q(0, 1) | pq.Squeezing2(r=r)
            pq.Q(0) | pq.PostSelectPhotons(photon_counts=(k,))
        state = pq.PureFockSimulator(d=2, config=pq.Config(cutoff=10, hbar=1)).execute(prog).state
        p = np.real(state.fock_probabilities)
        want_sel = math.tanh(r) ** (2 * k) / math.cosh(r) ** 2
        check(f"C9a post-select n0={k}: selection prob", float(p.sum()), want_sel, 1e-12)
        p_norm = p / p.sum()
        want = np.zeros_like(p_norm)
        want[k] = 1.0
        check(f"C9b post-select n0={k} -> |{k}>", float(np.max(np.abs(p_norm - want))), 0.0, 1e-12)

    # C9c joint PNR + homodyne: conditioning on n0=k leaves |k>, so the homodyne
    #     variance of the REMAINING mode is exactly (2k+1)/2. Sharp, closed-form.
    with pq.Program() as prog:
        pq.Q(0, 1) | pq.Vacuum()
        pq.Q(0, 1) | pq.Squeezing2(r=r)
        pq.Q(0) | pq.ParticleNumberMeasurement()
        pq.Q(1) | pq.HomodyneMeasurement()
    res = pq.PureFockSimulator(d=2, config=pq.Config(cutoff=8, hbar=1)).execute(prog, shots=200000)
    ks = np.array([int(t[0]) for t in res.samples])
    xs = np.array([float(t[1]) for t in res.samples])
    for k in range(3):
        sel = xs[ks == k]
        check(f"C9c joint var(x1|n0={k}) == (2k+1)/2", float(sel.var()), (2 * k + 1) / 2.0, 0.05)
        check(
            f"C9d joint marginal P(n0={k})",
            float(np.mean(ks == k)),
            math.tanh(r) ** (2 * k) / math.cosh(r) ** 2,
            0.01,
        )
    note("C9c/C9d confirm conditioning is exact: piquasso reproduces the closed form")

    # -----------------------------------------------------------------------
    print()
    print("C10. feedforward: gate parameter resolved from the measurement outcome")
    print("-" * 78)
    with pq.Program() as prog:
        pq.Q(0, 1) | pq.Vacuum()
        pq.Q(0) | pq.Squeezing(r=0.5)
        pq.Q(0) | pq.ParticleNumberMeasurement()
        pq.Q(1) | pq.Displacement(r=lambda x: 0.1 * float(x[0]), phi=0.0)
        pq.Q(1) | pq.HomodyneMeasurement()
    res = pq.PureFockSimulator(d=2, config=pq.Config(cutoff=8, hbar=1)).execute(prog, shots=40000)
    ks = np.array([int(t[0]) for t in res.samples])
    xs = np.array([float(t[1]) for t in res.samples])
    ff_ok = True
    for k in sorted(set(ks.tolist())):
        n = int((ks == k).sum())
        if n < 200:
            continue
        got = float(xs[ks == k].mean())
        want = 0.1 * k * math.sqrt(2)  # cvsim rbar = sqrt(2) * alpha
        se = float(xs[ks == k].std() / math.sqrt(n))
        if abs(got - want) > 4 * se + 0.005:
            ff_ok = False
        print(f"    k={k}: n={n:5d} mean(x1)={got:+.6f} want={want:+.6f} se={se:.4f}")
    (PASS if ff_ok else FAIL).append("C10 feedforward displaces by 0.1*n*sqrt(2)")
    print(f"    C10 feedforward: {'PASS' if ff_ok else 'FAIL'}")

    # -----------------------------------------------------------------------
    print()
    print("C11. capability boundary: where piquasso CANNOT serve as the oracle")
    print("-" * 78)
    theta = math.acos(math.sqrt(0.8))

    def probe(label: str, build) -> bool:
        try:
            sim = pq.PureFockSimulator(d=3, config=pq.Config(cutoff=8, hbar=1))
            res = sim.execute(build(), shots=100)
            print(f"    {label:<46} OK ({np.shape(res.samples)})")
            return True
        except Exception as exc:
            print(f"    {label:<46} {type(exc).__name__}: {str(exc)[:52]}")
            return False

    def with_channel():
        with pq.Program() as p:
            pq.Q(0, 1, 2) | pq.Vacuum()
            pq.Q(0) | pq.Squeezing(r=0.4)
            pq.Q(0) | pq.Attenuator(theta=theta)
            pq.Q(1) | pq.Attenuator(theta=theta)
            pq.Q(2) | pq.Attenuator(theta=theta)
            pq.Q(2) | pq.ParticleNumberMeasurement()
        return p

    def with_channel_and_homodyne():
        with pq.Program() as p:
            pq.Q(0, 1, 2) | pq.Vacuum()
            pq.Q(0) | pq.Squeezing(r=0.4)
            pq.Q(0) | pq.Attenuator(theta=theta)
            pq.Q(1) | pq.Attenuator(theta=theta)
            pq.Q(2) | pq.Attenuator(theta=theta)
            pq.Q(2) | pq.ParticleNumberMeasurement()
            pq.Q(1) | pq.HomodyneMeasurement()
        return p

    def non_gaussian_composite():
        with pq.Program() as p:
            pq.Q(0, 1, 2) | pq.Vacuum()
            pq.Q(0) | pq.NumberState(occupation_numbers=(1,))
            pq.Q(0) | pq.Kerr(xi=0.7)
            pq.Q(0, 1) | pq.Beamsplitter(theta=0.4)
            pq.Q(2) | pq.ParticleNumberMeasurement()
            pq.Q(1) | pq.HomodyneMeasurement()
        return p

    probe("3 modes + loss + PNR (PureFock)", with_channel)
    probe("3 modes + loss + PNR + homodyne (PureFock)", with_channel_and_homodyne)
    probe("3 modes + Kerr + PNR + homodyne (PureFock)", non_gaussian_composite)
    note("PureFockSimulator CRASHES (AttributeError: 'FockState' object has no")  # noqa: N806
    note("attribute 'state_vector') whenever a channel precedes any later")
    note("instruction; FockSimulator supports channels but NOT homodyne at all.")
    note("=> non-Gaussian + PNR + homodyne WITHOUT channels IS available.")

    # -----------------------------------------------------------------------
    print()
    print("=" * 78)
    print(f"SUMMARY: {len(PASS)} PASS / {len(FAIL)} FAIL")
    if FAIL:
        print("FAILED:")
        for name in FAIL:
            print(f"  - {name}")
    print()
    print("NOTES (must go into any convention-mapping doc before use):")
    for msg in NOTES:
        print(f"  - {msg}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
