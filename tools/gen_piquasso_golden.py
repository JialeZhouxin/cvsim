"""Generate piquasso golden data for the Fock composite / conditioning gap.

WHY THIS EXISTS
---------------
``tests/_golden/sf_fock_golden.npz`` (Strawberry Fields 0.23.0) covers single- and
two-mode *gate evolutions* only: 8 cases, <=2 modes, **no 3+ mode circuit, no
measurement, no conditioning, no channel**. That is precisely where cvsim has no
closed form to lean on.

piquasso 8.0.1 was qualified first (``tools/qualify_piquasso_oracle.py``): 43
closed-form checks all pass at <=1e-12, including exact measurement conditioning.
So its output is trustworthy enough to freeze as an independent oracle for exactly
those uncovered features.

WHAT IS FROZEN
--------------
Only what SF's golden does NOT cover:
  * 3-mode and 4-mode non-Gaussian gate chains (the "3+ mode" hole)
  * PNR joint distribution of a 3-mode composite
  * PNR post-selection / conditioning on a 3-mode composite

DESIGN RULE (differs from tools/gen_sf_golden.py on purpose)
------------------------------------------------------------
This script **never gates on cvsim**. ``gen_sf_golden.py`` computes
``max|SF - cvsim| < 1e-8`` and exits without writing if it fails, which means it
can only ever *lock in* an existing agreement — it cannot discover a disagreement.
Here the reference output is written as-is; the cvsim comparison printed at the end
is informational only. A disagreement must show up as a RED TEST, not as a refusal
to generate.

RUN (throwaway venv; piquasso is deliberately NOT a project dependency)
----------------------------------------------------------------------
    uv venv <tmp> --python 3.13
    uv pip install --python <tmp>/Scripts/python.exe piquasso
    <tmp>/Scripts/python.exe tools/gen_piquasso_golden.py

Output: ``tests/_golden/piquasso_fock_composite_golden.npz``, read by
``tests/test_piquasso_golden.py`` (numpy only, no piquasso at test time).

CONVENTIONS (all pinned empirically in docs/piquasso-golden-roundtrip.md)
------------------------------------------------------------------------
* ``Config(hbar=1)`` -> piquasso ``xxpp`` cov/mean equal cvsim ``2V`` / ``rbar``.
* tensor axis order: identical; ``get_tensor_representation()`` gives the dense
  per-mode array of shape ``(cutoff,)*nmode``.
* beamsplitter: cvsim ``(theta, phi)`` == piquasso ``(-theta, -phi)`` (1.1e-16).
  squeeze / displace / kerr / two_mode_squeeze: same sign.
* ``Config(cutoff=N)`` is a **TOTAL photon-number** cutoff in piquasso
  (``sum_i n_i < N``; ``state_vector`` length == C(N+m-1, m)), but a **PER-MODE**
  cutoff in cvsim. The dense tensors therefore agree only on piquasso's simplex,
  which is why agreement improves as ``N`` grows.
* NEVER write ``pq.Vacuum()`` before ``pq.NumberState(...)``: preparations are
  ADDITIVE (a superposition), not replacements.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import piquasso as pq

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "tests" / "_golden" / "piquasso_fock_composite_golden.npz"

HBAR = 1  # cvsim convention

# --- case definitions: (kind, modes, params) --------------------------------

# 3-mode non-Gaussian chain: squeeze, displace, Kerr, two BS, Kerr.
CHAIN3_A = [
    ("squeeze", (0,), {"r": 0.3}),
    ("displace", (1,), {"alpha": 0.25 * np.exp(1j * 0.4)}),
    ("kerr", (2,), {"chi": 0.2}),
    ("bs", (0, 1), {"theta": 0.5, "phi": 0.0}),
    ("bs", (1, 2), {"theta": 0.4, "phi": 0.0}),
    ("kerr", (0,), {"chi": 0.1}),
]

# 3-mode composite used for the PNR / conditioning cases.
CHAIN3_B = [
    ("squeeze", (0,), {"r": 0.4}),
    ("kerr", (1,), {"chi": 0.5}),
    ("bs", (0, 1), {"theta": 0.6, "phi": 0.0}),
    ("bs", (1, 2), {"theta": 0.5, "phi": 0.0}),
]

# 4-mode chain: pushes past the 2-mode ceiling of the SF golden.
# Cutoffs chosen by a convergence sweep against cvsim (informational; the
# numbers are printed by _diagnostics below):
#   chain3_ket        4.3e-13 @ cutoff 40
#   chain4_ket        5.3e-12 @ cutoff 32
#   chain3_pnr_joint  2.5e-14 @ cutoff 28
#   post-selection    7.6e-13 @ cutoff 28
# The residual is dominated by the cutoff-semantics mismatch (piquasso truncates
# on TOTAL photon number, cvsim per mode), not by either side being wrong.
CHAIN4 = [
    ("squeeze", (0,), {"r": 0.25}),
    ("kerr", (1,), {"chi": 0.2}),
    ("bs", (0, 1), {"theta": 0.4, "phi": 0.0}),
    ("bs", (2, 3), {"theta": 0.35, "phi": 0.0}),
    ("kerr", (2,), {"chi": 0.15}),
    ("bs", (1, 2), {"theta": 0.3, "phi": 0.0}),
]

CUT_CHAIN3_A = 40
CUT_CHAIN4 = 32
CUT_CHAIN3_B = 28
POST_K = (0, 1, 2)


# --- piquasso appliers -------------------------------------------------------


def apply_pq(prog: pq.Program, ops: list, nmode: int) -> None:
    """Apply the op list to a piquasso program (BS sign is negated here)."""
    pq.Q(*range(nmode)) | pq.Vacuum()
    for kind, modes, prm in ops:
        if kind == "squeeze":
            pq.Q(modes[0]) | pq.Squeezing(r=prm["r"], phi=prm.get("phi", 0.0))
        elif kind == "displace":
            alpha = complex(prm["alpha"])
            pq.Q(modes[0]) | pq.Displacement(r=abs(alpha), phi=float(np.angle(alpha)))
        elif kind == "kerr":
            pq.Q(modes[0]) | pq.Kerr(xi=prm["chi"])
        elif kind == "bs":
            # cvsim(theta, phi) == piquasso(-theta, -phi)
            pq.Q(modes[0], modes[1]) | pq.Beamsplitter(
                theta=-prm["theta"], phi=-prm.get("phi", 0.0)
            )
        else:  # pragma: no cover - guard against typos in the tables above
            raise ValueError(f"unknown op {kind!r}")


def sim(nmode: int) -> pq.PureFockSimulator:
    return pq.PureFockSimulator(d=nmode, config=pq.Config(cutoff=0, hbar=HBAR))


def _sim(nmode: int, cutoff: int) -> pq.PureFockSimulator:
    return pq.PureFockSimulator(d=nmode, config=pq.Config(cutoff=cutoff, hbar=HBAR))


def run_ket(ops: list, nmode: int, cutoff: int) -> np.ndarray:
    """Dense amplitude tensor (cutoff,)*nmode for the op chain starting at vacuum."""
    with pq.Program() as prog:
        apply_pq(prog, ops, nmode)
    st = _sim(nmode, cutoff).execute(prog).state
    return np.asarray(st.get_tensor_representation(), dtype=np.complex128)


def run_prob_dense(ops: list, nmode: int, cutoff: int) -> np.ndarray:
    """Dense PNR probability tensor (cutoff,)*nmode from the occupation map."""
    with pq.Program() as prog:
        apply_pq(prog, ops, nmode)
    st = _sim(nmode, cutoff).execute(prog).state
    out = np.zeros((cutoff,) * nmode, dtype=np.float64)
    for key, val in st.fock_probabilities_map.items():
        out[tuple(int(k) for k in key)] = float(np.real(val))
    return out


def run_post_select(ops: list, mode: int, k: int, cutoff: int) -> tuple[np.ndarray, float]:
    """PNR post-select `mode` == k on an nmode chain.

    Returns (normalised joint density over the REMAINING modes, selection prob).
    PostSelectPhotons removes the measured mode, so an nmode chain yields an
    (nmode-1)-mode state.
    """
    nmode = max(max(m for _k, m, _p in ops)) + 1
    with pq.Program() as prog:
        apply_pq(prog, ops, nmode)
        pq.Q(mode) | pq.PostSelectPhotons(photon_counts=(k,))
    st = _sim(nmode, cutoff).execute(prog).state
    left = st.d
    dense = np.zeros((cutoff,) * left, dtype=np.float64)
    for key, val in st.fock_probabilities_map.items():
        dense[tuple(int(x) for x in key)] = float(np.real(val))
    sel = float(np.trace(np.asarray(st.density_matrix, dtype=np.complex128)).real)
    return dense / sel, sel


def main() -> None:
    out: dict[str, np.ndarray] = {}

    # 1. 3-mode non-Gaussian chain, dense ket
    out["chain3_ket"] = run_ket(CHAIN3_A, 3, CUT_CHAIN3_A)

    # 2. 4-mode chain, dense ket
    out["chain4_ket"] = run_ket(CHAIN4, 4, CUT_CHAIN4)

    # 3. 3-mode composite PNR joint distribution (dense probability tensor)
    out["chain3_pnr_joint"] = run_prob_dense(CHAIN3_B, 3, CUT_CHAIN3_B)

    # 4. PNR post-selection on the 3-mode composite -> normalised 2-mode joint
    sel = np.zeros(len(POST_K), dtype=np.float64)
    for i, k in enumerate(POST_K):
        joint, sel_i = run_post_select(CHAIN3_B, mode=1, k=k, cutoff=CUT_CHAIN3_B)
        out[f"chain3_post_k{k}_joint"] = joint
        sel[i] = sel_i
    out["chain3_post_selprobs"] = sel

    meta = {
        "tool": "tools/gen_piquasso_golden.py",
        "generated": date.today().isoformat(),
        "piquasso": pq.__version__,
        "numpy": np.__version__,
        "hbar": HBAR,
        "purpose": "Fock composite / 3+ modes / PNR conditioning (SF golden gap)",
        "cutoff_semantics": (
            "piquasso Config(cutoff=N) = TOTAL photon number (sum_i n_i < N); "
            "state_vector length == C(N+m-1, m). cvsim uses a PER-MODE cutoff. "
            "Dense tensors via get_tensor_representation() -> (N,)*m."
        ),
        "normalization": (
            "piquasso states are NOT renormalised after truncation; cvsim IS. "
            "Post-selected states here are divided by the selection probability."
        ),
        "conventions": {
            "beamsplitter": "cvsim(theta, phi) == piquasso(-theta, -phi)",
            "others": "squeeze / displace / kerr / two_mode_squeeze: same sign",
            "tensor_order": "identical axis order (mode 0 first)",
            "preparation": "never pq.Vacuum() then pq.NumberState() - additive",
        },
        "cases": {
            "chain3_ket": {"ops": str(CHAIN3_A), "cutoff": CUT_CHAIN3_A, "kind": "dense ket"},
            "chain4_ket": {"ops": str(CHAIN4), "cutoff": CUT_CHAIN4, "kind": "dense ket"},
            "chain3_pnr_joint": {
                "ops": str(CHAIN3_B),
                "cutoff": CUT_CHAIN3_B,
                "kind": "dense PNR probability tensor",
            },
            "chain3_post": {
                "ops": str(CHAIN3_B),
                "cutoff": CUT_CHAIN3_B,
                "conditioned_mode": 1,
                "k": list(POST_K),
                "kind": "normalised joint over remaining modes",
            },
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    # savez_compressed: the dense tensors are mostly zero outside piquasso's
    # total-photon simplex, so this shrinks 8.41 MB -> 0.22 MB.
    np.savez_compressed(
        OUT,
        **out,
        metadata=json.dumps(meta, indent=2).encode("utf-8"),
    )
    print(f"saved {OUT} ({OUT.stat().st_size / 1e6:.2f} MB)")
    for name, arr in sorted(out.items()):
        print(f"  {name:28s} shape={str(arr.shape):18s} dtype={arr.dtype}")


def _diagnostics() -> None:
    """Informational cvsim comparison. NEVER gates the write above."""
    import sys

    sys.path.insert(0, str(REPO))
    try:
        from cvsim.fock.circuit import FockCircuit
        from cvsim.fock.observables import pnr_condition
    except ImportError as exc:  # cvsim not importable -> skip silently
        print(f"\n[diagnostics skipped] {exc}")
        return

    def build_cv(ops: list, nmode: int, cutoff: int) -> FockCircuit:
        c = FockCircuit(nmode, cutoff=cutoff)
        for kind, modes, prm in ops:
            if kind == "squeeze":
                c.squeeze(modes[0], r=prm["r"], phi=prm.get("phi", 0.0))
            elif kind == "displace":
                c.displace(modes[0], alpha=prm["alpha"])
            elif kind == "kerr":
                c.kerr(modes[0], chi=prm["chi"])
            elif kind == "bs":
                c.beamsplitter(modes[0], modes[1], theta=prm["theta"], phi=prm.get("phi", 0.0))
        return c

    g = np.load(OUT)
    print("\n" + "=" * 74)
    print("DIAGNOSTICS (informational only - generation already done)")
    print("=" * 74)

    cv = build_cv(CHAIN3_A, 3, CUT_CHAIN3_A).run().amps
    print(f"chain3_ket            max|diff| = {np.max(np.abs(g['chain3_ket'] - cv)):.3e}")

    cv4 = build_cv(CHAIN4, 4, CUT_CHAIN4).run().amps
    print(f"chain4_ket            max|diff| = {np.max(np.abs(g['chain4_ket'] - cv4)):.3e}")

    cvb = build_cv(CHAIN3_B, 3, CUT_CHAIN3_B).run()
    prob = np.abs(cvb.amps) ** 2
    print(f"chain3_pnr_joint      max|diff| = {np.max(np.abs(g['chain3_pnr_joint'] - prob)):.3e}")

    for k in POST_K:
        post = pnr_condition(cvb, mode=1, n=k)
        p = np.abs(post.amps) ** 2
        p = p / p.sum()
        print(
            f"chain3_post_k{k}_joint  max|diff| = "
            f"{np.max(np.abs(g[f'chain3_post_k{k}_joint'] - p)):.3e}"
        )


if __name__ == "__main__":
    main()
    _diagnostics()
