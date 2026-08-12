"""Generate Strawberry Fields fock-backend golden density matrices (Phase F6).

One-off generation script: run inside an SF venv; the output npz is committed
to ``tests/_golden/sf_fock_golden.npz``. The comparison test suite
(``tests/test_sf_golden_f6.py``) reads only the npz — no SF runtime
dependency in the repo.

Usage (Windows venv path; Linux uses ``bin/python``):

    /tmp/sfenv/Scripts/python.exe tools/gen_sf_golden.py

Setup (once):

    uv venv /tmp/sfenv
    uv pip install --python /tmp/sfenv "strawberryfields" "setuptools<81"

Version lock (2026-08-12): strawberryfields 0.23.0 / thewalrus 0.22.0
(fock-backend gate matrices come from thewalrus) / numpy 2.5.2 /
scipy 1.18.0.

Environment shims (see docs/sf-roundtrip-fock.md):
- scipy>=1.15 renamed simps -> simpson; SF 0.23 imports
  ``scipy.integrate.simps`` at import time -> alias *before* importing SF.
- setuptools<81 keeps pkg_resources alive (strawberryfields.apps).

Baked-in empirical facts (2026-08-12 scans):
- fresh ``sf.Engine("fock", ...)`` per program: an engine instance reuses
  residual state from previous programs (observed cross-contamination).
- all golden stored as *density matrices* (complex128): SF 0.23 fock
  backend returns ``pure=False`` for Fock(n)-prepared states (``ket()`` is
  None); dm keeps relative phases and doubles as the density-export-format
  check (``FockDensity.rho`` vs ``state.dm()``). **Storage strategy (size):**
  pure gate-only evolutions store ket (s2_00/chain — 46 KB vs 77 MB as dm);
  Fock-prepared / mixed states store dm (rotated/kerr/bs_11/thermal).
- SF multi-mode ``state.dm()`` is a 2m-D tensor with axis order
  ``(n0, n0', n1, n1', ...)`` (einsum ``"ac,bd->abcd"``); transpose to
  ``(n0, n1, ..., n0', n1', ...)`` then C-order flatten to (N^m, N^m)
  == ``FockDensity.rho`` (empirically verified).
- per-case cutoffs from leakage scan (tanh^cutoff backflow): squeezed 50
  (6e-10), displaced 12 (7.6e-11), rotated/kerr/bs_11/thermal 10 (~0),
  s2_00 30 (3.6e-11), chain 45 (1.7e-11).
- BS phase mapping: cvsim ``beamsplitter(theta, phi)`` == SF
  ``BSgate(-theta, -phi)`` (full-tensor max|d| = 1.1e-16) -> cvsim side uses
  negated BS parameters.

Self-check before saving: diagonal coarse alignment + full-matrix agreement
vs cvsim (max|d| < 1e-8), printed per case.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

# scipy>=1.15 renamed simps -> simpson; SF 0.23 imports it at import time.
import scipy.integrate as _si

if not hasattr(_si, "simps"):
    _si.simps = _si.simpson

import strawberryfields as sf
from strawberryfields.ops import (
    BSgate,
    Dgate,
    Fock,
    Kgate,
    Rgate,
    S2gate,
    Sgate,
    Thermal,
)

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))  # cvsim is pure numpy/scipy — importable in the SF venv

from cvsim.fock.density import FockDensity  # noqa: E402
from cvsim.fock.gates import (  # noqa: E402
    beamsplitter,
    displace,
    kerr,
    phase,
    squeeze,
    two_mode_squeeze,
)
from cvsim.fock.state import FockState  # noqa: E402

OUT = REPO / "tests" / "_golden" / "sf_fock_golden.npz"


def sf_dm(prog: sf.Program, cutoff: int) -> np.ndarray:
    """Run ``prog`` on a *fresh* fock engine; return state.dm() as complex128.

    Multi-mode dm comes back as a 2m-D tensor with axes (n0, n0', n1, n1',
    ...); transpose to (n0, n1, ..., n0', n1', ...) and C-order flatten so
    the result matches ``FockDensity.rho`` ((N^m, N^m)) element-wise.
    """
    eng = sf.Engine("fock", backend_options={"cutoff_dim": cutoff})
    dm = np.asarray(eng.run(prog).state.dm(), dtype=np.complex128)
    m = dm.ndim // 2
    if m == 1:
        return dm
    perm = list(range(0, 2 * m, 2)) + list(range(1, 2 * m, 2))
    dm = dm.transpose(perm)
    rows = int(np.prod(dm.shape[:m]))
    return dm.reshape(rows, rows)


def sf_ket(prog: sf.Program, cutoff: int) -> np.ndarray:
    """Run ``prog`` on a *fresh* fock engine; return ket C-order flattened.

    Pure gate-only evolutions keep ``pure=True`` so ``ket()`` works; the
    2m-D amplitude tensor has axes (n0, n1, ...) already (no transpose).
    """
    eng = sf.Engine("fock", backend_options={"cutoff_dim": cutoff})
    ket = np.asarray(eng.run(prog).state.ket(), dtype=np.complex128)
    return ket.ravel()


def cvsim_rho_of_pure(state: FockState) -> np.ndarray:
    return FockDensity.from_pure(state).rho


def main() -> None:
    # (name, SF program, cvsim rho, description, cutoff)
    cases: list[tuple[str, np.ndarray, np.ndarray, str, int]] = []

    # 1. squeezed@50 — S(0.5)|0>
    prog = sf.Program(1)
    with prog.context as q:
        Sgate(0.5) | q[0]
    cases.append(
        (
            "squeezed_r05",
            sf_dm(prog, 50),
            cvsim_rho_of_pure(FockState.squeezed(50, 0.5)),
            "S(0.5)|0>",
            50,
        )
    )

    # 2. displaced@12 — D(0.4, 0.3)|0> = |0.4 e^{0.3i}>
    prog = sf.Program(1)
    with prog.context as q:
        Dgate(0.4, 0.3) | q[0]
    cases.append(
        (
            "displaced",
            sf_dm(prog, 12),
            cvsim_rho_of_pure(displace(FockState.vacuum(12), 0.4 * np.exp(1j * 0.3))),
            "D(0.4,0.3)|0>",
            12,
        )
    )

    # 3. rotated@10 — R(0.6)|1>
    prog = sf.Program(1)
    with prog.context as q:
        Fock(1) | q[0]
        Rgate(0.6) | q[0]
    cases.append(
        (
            "rotated",
            sf_dm(prog, 10),
            cvsim_rho_of_pure(phase(FockState.fock(1, 10), 0.6)),
            "R(0.6)|1>",
            10,
        )
    )

    # 4. kerr@10 — K(0.1)|1>
    prog = sf.Program(1)
    with prog.context as q:
        Fock(1) | q[0]
        Kgate(0.1) | q[0]
    cases.append(
        (
            "kerr",
            sf_dm(prog, 10),
            cvsim_rho_of_pure(kerr(FockState.fock(1, 10), 0.1)),
            "K(0.1)|1>",
            10,
        )
    )

    # 5. bs_11@10 — BS(pi/4, 0.2)|1,1>; cvsim side uses negated params (BS mapping)
    prog = sf.Program(2)
    with prog.context as q:
        Fock(1) | q[0]
        Fock(1) | q[1]
        BSgate(np.pi / 4, 0.2) | (q[0], q[1])
    cases.append(
        (
            "bs_11",
            sf_dm(prog, 10),
            cvsim_rho_of_pure(
                beamsplitter(FockState.fock2(1, 1, 10), -np.pi / 4, -0.2)
            ),
            "BS(pi/4,0.2)|1,1>",
            10,
        )
    )

    # 6. s2_00@30 — S2(0.5)|0,0>
    prog = sf.Program(2)
    with prog.context as q:
        S2gate(0.5) | (q[0], q[1])
    cases.append(
        (
            "s2_00",
            sf_ket(prog, 30),
            two_mode_squeeze(FockState.vacuum(30, 2), 0.5).amps.ravel(),
            "S2(0.5)|0,0>",
            30,
        )
    )

    # 7. chain@45 — S(0.4)@m0, D(0.3,0.2)@m0, D(0.2,0.5)@m1, BS(0.8,0.4), K(0.1)@m1
    prog = sf.Program(2)
    with prog.context as q:
        Sgate(0.4) | q[0]
        Dgate(0.3, 0.2) | q[0]
        Dgate(0.2, 0.5) | q[1]
        BSgate(0.8, 0.4) | (q[0], q[1])
        Kgate(0.1) | q[1]
    st = FockState.vacuum(45, 2)
    st = squeeze(st, 0.4, mode=0)
    st = displace(st, 0.3 * np.exp(1j * 0.2), mode=0)
    st = displace(st, 0.2 * np.exp(1j * 0.5), mode=1)
    st = beamsplitter(st, -0.8, -0.4)  # SF BSgate(0.8, 0.4) -> negated (BS mapping)
    st = kerr(st, 0.1, mode=1)
    cases.append(
        (
            "chain",
            sf_ket(prog, 45),
            st.amps.ravel(),
            "S(0.4)D(0.3,0.2)D(0.2,0.5)BS(0.8,0.4)K(0.1)",
            45,
        )
    )

    # 8. thermal_dm@10 — thermal nbar=1.0
    prog = sf.Program(1)
    with prog.context as q:
        Thermal(1.0) | q[0]
    cases.append(
        (
            "thermal_dm",
            sf_dm(prog, 10),
            FockDensity.thermal(10, 1.0).rho,
            "thermal nbar=1.0",
            10,
        )
    )

    # Self-check: diagonal coarse alignment + full-matrix agreement.
    meta_cases = {}
    ok = True
    for name, sf_rho, cv_rho, desc, cutoff in cases:
        if sf_rho.shape != cv_rho.shape:
            print(f"FAIL {name}: shape {sf_rho.shape} vs {cv_rho.shape}")
            ok = False
            continue
        diag = float(np.max(np.abs(np.diag(sf_rho) - np.diag(cv_rho))))
        full = float(np.max(np.abs(sf_rho - cv_rho)))
        if full >= 1e-8:
            ok = False
        print(
            f"{'OK  ' if full < 1e-8 else 'FAIL'} {name:12s} "
            f"shape={sf_rho.shape} diag|d|={diag:.2e} full|d|={full:.2e} ({desc})"
        )
        meta_cases[name] = {"cutoff": cutoff, "description": desc}

    if not ok:
        sys.exit("self-check failed — npz NOT written")

    import scipy
    import thewalrus

    meta = {
        "tool": "tools/gen_sf_golden.py",
        "generated": date.today().isoformat(),
        "strawberryfields": sf.__version__,
        "thewalrus": thewalrus.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "engine": "fock",
        "basis_order": "dm axes (n0,n0',n1,n1') -> transpose(0,2,1,3) -> C-order (N^m,N^m)",
        "cases": meta_cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        OUT,
        squeezed_r05=cases[0][1],
        displaced=cases[1][1],
        rotated=cases[2][1],
        kerr=cases[3][1],
        bs_11=cases[4][1],
        s2_00=cases[5][1],
        chain=cases[6][1],
        thermal_dm=cases[7][1],
        metadata=json.dumps(meta, indent=2).encode('utf-8'),  # bytes: native dtype, no allow_pickle needed
    )
    print(f"saved {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
