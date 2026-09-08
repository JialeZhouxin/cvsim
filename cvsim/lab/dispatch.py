"""Lab dispatch — `/run` `/sample` `/batch` 的唯一执行入口 (ADR-0010)。

按 ``LabCircuit.backend`` 路由到三表示 runner（注册表一行一后端）；
server 零 backend 特判、零 runner import、零 rng 构造（``rng=None`` 时由
``circuit.seed`` 派生，:func:`sample_circuit` 显式 rng 仍是测试注入通道）。
gaussian 的执行体与 fock/bosonic runner 同形（执行 + LabResult 组装住在
各自 backend 模块）；本模块不做物理，只做分派。
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from cvsim.lab.bosonic_backend import run_bosonic_circuit
from cvsim.lab.fock_backend import batch_fock_circuit, run_fock_circuit
from cvsim.lab.gaussian_backend import run_gaussian_circuit
from cvsim.lab.ir import LabCircuit
from cvsim.lab.result import LabResult

#: Runner registry (ADR-0010 #1): one row per backend. Every runner shares
#: the shape ``(circuit, rng, *, sampled, steps) -> LabResult`` — ``steps``
#: is accepted-and-ignored everywhere so routing needs no per-backend branches.
_RUNNERS: dict[str, Callable[..., LabResult]] = {
    "gaussian": run_gaussian_circuit,
    "fock": run_fock_circuit,
    "bosonic": run_bosonic_circuit,
}

#: Batch registry (ADR-0010 #8 follow-up): /batch executor per backend.
#: fock-only is a physical fact (R4: v0 has no Gaussian batch, bosonic
#: batch-sampling is exactly its PNR surface) — missing key = honest 422 at
#: the route gate, never a fabricated empty batch. Callable returns the
#: JSON-ready histogram payload (batch side stays outside LabResult,
#: ADR-0008 decision 5).
_BATCHERS: dict[str, Callable[[LabCircuit, int, int], dict]] = {
    "fock": batch_fock_circuit,
}


def run_circuit(circuit: LabCircuit) -> LabResult:
    """Mean path: ordered ops → LabResult. Pure, no RNG (deterministic
    runners; bosonic uses a seeded Generator derived from ``circuit.seed``)."""
    runner = _RUNNERS[circuit.backend]
    rng = np.random.default_rng(circuit.seed) if circuit.backend != "gaussian" else None
    detail = getattr(circuit, "detail", None)
    if circuit.backend == "bosonic":
        return runner(circuit, rng, steps=(detail == "steps"))
    return runner(circuit, rng)



def sample_circuit(circuit: LabCircuit, rng: np.random.Generator | None = None) -> LabResult:
    """Sample path: true sampling of every measurement node, in node order;
    each measurement conditions the state for the next one. ``rng=None``
    derives a Generator from ``circuit.seed`` (deterministic per circuit);
    an explicit Generator is the test injection channel. Either way the
    LabResult carries the sampled contract keys (seed/sampled)."""
    if rng is None:
        rng = np.random.default_rng(circuit.seed)
    runner = _RUNNERS[circuit.backend]
    detail = getattr(circuit, "detail", None)
    if circuit.backend == "bosonic":
        return runner(circuit, rng, sampled=True, steps=(detail == "steps"))
    return runner(circuit, rng, sampled=True)

def batch_circuit(circuit: LabCircuit, shots: int, seed: int) -> dict:
    """Batch path (R4): fock-only exact-distribution batch sampling.

    Dispatch twin of :func:`run_circuit` for the ``/batch`` route: the
    server hands over a loaded LabCircuit + validated shots and gets the
    JSON-ready histogram — zero runner knowledge at the route layer.
    Unknown backend = KeyError, caught at the route gate as a domain 422
    (server owns the user-facing message, ADR-0010 #7 gate discipline).
    """
    return _BATCHERS[circuit.backend](circuit, shots, seed)
