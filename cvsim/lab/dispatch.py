"""Lab dispatch — `/run` `/sample` `/batch` 的唯一执行入口 (ADR-0010)。

按 ``LabCircuit.backend`` 路由到三表示 runner（注册表一行一后端）；
server 零 backend 特判、零 runner import、零 rng 构造（``rng=None`` 时由
``circuit.seed`` 派生，:func:`sample_circuit` 显式 rng 仍是测试注入通道）。
gaussian 的执行体与 fock/bosonic runner 同形（执行 + LabResult 组装住在
各自 backend 模块）；本模块不做物理，只做分派。

**分派零特判**：三个 runner 的签名本就统一为
``(circuit, rng, *, sampled, steps)``，故调用点可以无分支地一律传全；
``steps`` 一律传即可（唯一有断点中间态的 bosonic **自己读** ``circuit.detail``，
ADR-0010 #4，故它不吃这个参数也不丢快照）。

唯一不能靠签名统一的是 ``rng`` 的**语义**，且那是物理事实：

* gaussian 的 ``rng=None`` 意为"走均值路径、不做真采样"
  （``_apply_measure`` 里 ``rng is None`` → ``homodyne_mean``），
  给了 rng 才是逐测量节点真采样。故 ``/run`` 下它**必须**收到 ``None``。
* bosonic 的 ``rng=None`` 只是"没给生成器"，其测量层会自造一个**未播种**的
  ``default_rng()`` → 同 seed 的两次运行结果不同。故 ``/run`` 下也必须派生。
* fock 的 ``rng=None`` 同样会让测量层自造未播种生成器，但
  ``run_fock_circuit`` **自己兜了** ``default_rng(circuit.seed)`` —— 所以
  dispatch 是否派生对它是**行为冗余**（``wants_rng=True`` 是防御性声明：把
  "由 dispatch 保证播种"写明，而不是依赖 runner 内部的兜底）。已实测：把它的
  标志翻成 ``False`` 不改变可复现性，只有 bosonic 会。

所以 ``rng`` 该不该派生**同时取决于后端和动词**：``/run`` 下 gaussian 要 ``None``、
bosonic 要派生；``/sample`` 下三者都要派生（gaussian 收到 rng 才真采样）。
这就是注册表行携带 ``wants_rng`` 的原因 —— 它把"该后端在**非采样**路径下要不要
派生 rng"写进数据，而不是写成路由体里的 ``if circuit.backend == ...``
（那正是 ADR-0010 #1 "一行一后端"失效的形态：接第四个后端要么被分支漏掉，
要么得回来改本模块）。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple

import numpy as np

from cvsim.lab.bosonic_backend import run_bosonic_circuit
from cvsim.lab.fock_backend import batch_fock_circuit, run_fock_circuit
from cvsim.lab.gaussian_backend import run_gaussian_circuit
from cvsim.lab.ir import LabCircuit
from cvsim.lab.result import LabResult


class _Runner(NamedTuple):
    """Registry row (ADR-0010 #1): every runner shares the signature
    ``(circuit, rng, *, sampled, steps) -> LabResult``; the flag declares the
    one thing a uniform signature cannot — how *this* backend reads ``rng``.

    ``wants_rng``: on the **non-sampling** path, derive a seed-seeded Generator
    and pass it. True for backends whose measurement layer would otherwise
    build an unseeded generator (fock/bosonic ⇒ non-reproducible per seed).
    False for gaussian, where ``None`` is the mean-path signal.
    """

    callable: Callable[..., LabResult]
    wants_rng: bool


#: Runner registry (ADR-0010 #1): one row per backend, the rng difference
#: declared in the row. New representation = add a row, do not touch routing.
_RUNNERS: dict[str, _Runner] = {
    "gaussian": _Runner(run_gaussian_circuit, wants_rng=False),
    "fock": _Runner(run_fock_circuit, wants_rng=True),
    "bosonic": _Runner(run_bosonic_circuit, wants_rng=True),
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


def _invoke(
    circuit: LabCircuit,
    *,
    sampled: bool,
    rng: np.random.Generator | None = None,
) -> LabResult:
    """The single routing body: one registry lookup, one uniform call.

    ``rng`` resolution, in order: an explicitly supplied Generator always
    wins (test injection channel); otherwise the sampling path always derives
    one from ``circuit.seed``; only the non-sampling path consults
    ``wants_rng`` (gaussian keeps ``None`` = mean path).
    """
    row = _RUNNERS[circuit.backend]
    if rng is None and (sampled or row.wants_rng):
        rng = np.random.default_rng(circuit.seed)
    return row.callable(
        circuit,
        rng,
        sampled=sampled,
        steps=(circuit.detail == "steps"),
    )


def run_circuit(circuit: LabCircuit) -> LabResult:
    """Mean path: ordered ops → LabResult. Pure, no RNG (deterministic
    runners; bosonic uses a seeded Generator derived from ``circuit.seed``)."""
    return _invoke(circuit, sampled=False)


def sample_circuit(circuit: LabCircuit, rng: np.random.Generator | None = None) -> LabResult:
    """Sample path: true sampling of every measurement node, in node order;
    each measurement conditions the state for the next one. ``rng=None``
    derives a Generator from ``circuit.seed`` (deterministic per circuit);
    an explicit Generator is the test injection channel. Either way the
    LabResult carries the sampled contract keys (seed/sampled)."""
    return _invoke(circuit, sampled=True, rng=rng)


def batch_circuit(circuit: LabCircuit, shots: int, seed: int) -> dict:
    """Batch path (R4): fock-only exact-distribution batch sampling.

    Dispatch twin of :func:`run_circuit` for the ``/batch`` route: the
    server hands over a loaded LabCircuit + validated shots and gets the
    JSON-ready histogram — zero runner knowledge at the route layer.
    Unknown backend = KeyError, caught at the route gate as a domain 422
    (server owns the user-facing message, ADR-0010 #7 gate discipline).
    """
    return _BATCHERS[circuit.backend](circuit, shots, seed)
