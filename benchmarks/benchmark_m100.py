"""m=100 benchmark + CI (vision Phase 3 exit #2/#5).

Times compile vs naive execution of a random passive circuit; asserts a
time budget (default 2s) so a perf regression fails CI, and records the
result to latest.json for cross-commit tracking.

Usage:
    python benchmarks/benchmark_m100.py [--m 100] [--depth 100]
                                        [--budget 2.0] [--seed 42]

Exit codes: 0 pass · 2 budget exceeded · 3 equivalence mismatch.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone

import numpy as np

from cvsim.gaussian import GaussianCircuit
from cvsim.gaussian.compile import _run_op
from cvsim.gaussian.state import GaussianState

HERE = __file__.rsplit("/", 1)[0] if "/" in __file__ else "benchmarks"
RESULT_PATH = f"{HERE}/latest.json"


def random_circuit(nmode: int, depth: int, seed: int) -> GaussianCircuit:
    rng = np.random.default_rng(seed)
    c = GaussianCircuit(nmode)
    for _ in range(depth):
        kind = int(rng.integers(0, 4))
        m1 = int(rng.integers(0, nmode))
        m2 = int(rng.integers(0, nmode - 1))
        if m2 >= m1:
            m2 += 1
        if kind == 0:
            c.squeeze(m1, float(rng.uniform(0, 1)), float(rng.uniform(0, 2 * np.pi)))
        elif kind == 1:
            c.phase(m1, float(rng.uniform(0, 2 * np.pi)))
        elif kind == 2:
            c.beamsplitter(
                m1, m2, float(rng.uniform(0, np.pi)), float(rng.uniform(0, 2 * np.pi))
            )
        else:
            c.mach_zehnder(
                m1, m2, float(rng.uniform(0, np.pi)), float(rng.uniform(0, np.pi))
            )
    return c


def naive_run(circ: GaussianCircuit) -> GaussianState:
    """Uncompiled path: per-op dispatch (mirrors test_compile.py naive)."""
    st = GaussianState.vacuum(circ.nmode)
    for op in circ._ops:
        st, _ = _run_op(op, st, {}, {}, rng=None)
    return st


def best_time(fn, repeat: int = 3) -> float:
    best = float("inf")
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t0)
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--m", type=int, default=100)
    ap.add_argument("--depth", type=int, default=100)
    ap.add_argument("--budget", type=float, default=2.0)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    circ = random_circuit(args.m, args.depth, args.seed)

    t_compile = best_time(circ.compile)
    compiled = circ.compile()
    t_compiled_run = best_time(compiled.run)
    t_naive = best_time(lambda: naive_run(circ))

    # Equivalence gate (same tolerance tier as tests/test_compile.py).
    st_compiled = compiled.run()
    st_naive = naive_run(circ)
    if not (
        np.allclose(st_compiled.V, st_naive.V, atol=1e-10)
        and np.allclose(st_compiled.rbar, st_naive.rbar, atol=1e-12)
    ):
        print(f"[bench] FAIL: compiled vs naive mismatch (m={args.m})")
        return 3

    total = t_compile + t_compiled_run
    passed = total <= args.budget
    result = {
        "schema": 1,
        "m": args.m,
        "depth": args.depth,
        "seed": args.seed,
        "commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True
        ).stdout.strip(),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "t_compile_s": round(t_compile, 6),
        "t_compiled_run_s": round(t_compiled_run, 6),
        "t_naive_s": round(t_naive, 6),
        "speedup": round(t_naive / t_compiled_run, 3) if t_compiled_run else None,
        "budget_s": args.budget,
        "passed": passed,
    }
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(
        f"[bench] m={args.m} depth={args.depth} | compile={t_compile*1e3:.2f}ms "
        f"run={t_compiled_run*1e3:.2f}ms total={total*1e3:.2f}ms "
        f"(budget {args.budget*1e3:.0f}ms) | naive={t_naive*1e3:.2f}ms "
        f"speedup={result['speedup']}x | {'PASS' if passed else 'FAIL'}"
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
