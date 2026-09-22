"""Lab dispatch: run/sample 单点分派 (ADR-0010) — 行为 + 结构守卫。

行为测试打在 dispatch 公开 interface 上（双动词，rng=None 由 circuit.seed
派生）；结构守卫是 ADR-0010 #8 的换防合同（AST 级，不 import cvsim）。
"""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pytest

from cvsim.lab import LabResult, load_circuit

# ---------------------------------------------------------------------------
# fixtures — 三后端同一物理场景（squeeze 0.1）
# ---------------------------------------------------------------------------

def _v1_body(backend: str, **extra) -> dict:
    body = {
        "schema": "circuit_v1",
        "nmode": 1,
        "backend": backend,
        "seed": 7,
        "ops": [{"id": "s", "op": "squeeze", "modes": [0], "params": {"r": 0.1}}],
        "view": {"wigner_mode": 0, "lim": 4.0, "n": 16},
    }
    body.update(extra)
    return body


def _gaussian_body() -> dict:
    return {
        "schema": "circuit_v1",
        "nmode": 1,
        "seed": 7,
        "ops": [{"id": "s", "op": "squeeze", "modes": [0], "params": {"r": 0.1, "phi": 0.0}}],
        "view": {"wigner_mode": 0, "lim": 4.0, "n": 16},
    }


# ---------------------------------------------------------------------------
# 1. dispatch 双动词：三后端全部走同一 interface
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("backend", ["gaussian", "fock", "bosonic"])
def test_run_circuit_all_backends_via_dispatch(backend: str) -> None:
    """run_circuit 是三后端的唯一入口：返回 LabResult 且自报家门。"""
    from cvsim.lab import dispatch

    body = _v1_body(backend)
    if backend == "gaussian":
        body = _gaussian_body()
    result = dispatch.run_circuit(load_circuit(body))
    assert isinstance(result, LabResult)
    assert result.backend == backend
    assert result.nmode == 1


@pytest.mark.parametrize("backend", ["gaussian", "fock", "bosonic"])
def test_sample_circuit_all_backends_via_dispatch(backend: str) -> None:
    """sample_circuit 带 sampled 契约键（seed/sampled 入 LabResult）。"""
    from cvsim.lab import dispatch

    body = _v1_body(backend)
    if backend == "gaussian":
        body = _gaussian_body()
    result = dispatch.sample_circuit(load_circuit(body))
    assert isinstance(result, LabResult)
    assert result.sampled is True
    assert result.seed == 7


def test_dispatch_rng_none_derives_from_seed() -> None:
    """rng=None → dispatch 用 circuit.seed 派生：同 seed 两次运行 measured
    一致（fock 有真采样路径，最能暴露 rng 是否真的接上了）。"""
    from cvsim.lab import dispatch

    body = _v1_body("fock", ops=[
        {"id": "s", "op": "squeeze", "modes": [0], "params": {"r": 0.1}},
        {"id": "m", "op": "measure_homodyne", "modes": [0], "params": {"name": "hd"}},
    ])
    r1 = dispatch.sample_circuit(load_circuit(body))
    r2 = dispatch.sample_circuit(load_circuit(body))
    assert r1.measured == r2.measured


def test_dispatch_rng_injection_still_works() -> None:
    """显式 rng 仍被尊重（测试注入通道，ADR-0010 双动词签名）。"""
    from cvsim.lab import dispatch

    body = _v1_body("fock", ops=[
        {"id": "m", "op": "measure_homodyne", "modes": [0], "params": {"name": "hd"}},
    ])
    rng_a = np.random.default_rng(3)
    rng_b = np.random.default_rng(3)
    a = dispatch.sample_circuit(load_circuit(body), rng=rng_a)
    b = dispatch.sample_circuit(load_circuit(body), rng=rng_b)
    assert a.measured == b.measured  # 同 seed 的两个 Generator → 同结果


def test_dispatch_unknown_backend_raises() -> None:
    """注册表外的 backend：显式 KeyError，不静默落 gaussian。"""
    from cvsim.lab import dispatch

    circuit = load_circuit(_v1_body("fock"))
    circuit.backend = "quantum_dots"  # type: ignore[assignment]
    with pytest.raises(KeyError):
        dispatch.run_circuit(circuit)


# ---------------------------------------------------------------------------
# 1b. detail=steps 升格为 LabCircuit 扩展字段（ADR-0010 #4）
# ---------------------------------------------------------------------------

def test_detail_steps_loads_into_labcircuit() -> None:
    """detail 是 load 层解析的扩展字段：bosonic circuit.detail == 'steps'。"""
    circuit = load_circuit(_v1_body("bosonic", detail="steps"))
    assert circuit.detail == "steps"


def test_detail_absent_is_none() -> None:
    circuit = load_circuit(_v1_body("bosonic"))
    assert circuit.detail is None


@pytest.mark.parametrize("bad", ["snapshot", True, 3, "step"])
def test_detail_invalid_value_rejected(bad: object) -> None:
    """detail 只接受 None|'steps'：其余值 422（422 契约，不静默忽略）。"""
    from cvsim.lab import CircuitV0Error

    with pytest.raises(CircuitV0Error, match="detail"):
        load_circuit(_v1_body("bosonic", detail=bad))


def test_detail_steps_reaches_bosonic_runner_via_server() -> None:
    """端到端：/run + detail=steps 仍返回分步快照（steps 线程不因搬家断）。"""
    from fastapi.testclient import TestClient

    from cvsim.lab.server import app

    body = _v1_body("bosonic", detail="steps", initial=["gkp0"], ops=[
        {"id": "l", "op": "loss", "modes": [0], "params": {"T": 0.9}},
        {"id": "m", "op": "measure_homodyne", "modes": [0], "params": {"name": "hd"}},
    ])
    tc = TestClient(app)
    r = tc.post("/run", json=body)
    assert r.status_code == 200, r.json()
    assert "steps" in r.json() and len(r.json()["steps"]) >= 1


def test_run_without_detail_has_no_steps_key() -> None:
    """无 detail → 无 steps 键（序列化省略 falsy extensions，字节不变）。"""
    from fastapi.testclient import TestClient

    from cvsim.lab.server import app

    tc = TestClient(app)
    r = tc.post("/run", json=_v1_body("bosonic", initial=["gkp0"]))
    assert r.status_code == 200
    assert "steps" not in r.json()


# ---------------------------------------------------------------------------
# 2. 顶层 re-export 不变（test_lab_ir 等调用面零改动存活）
# ---------------------------------------------------------------------------

def test_top_level_verbs_reexport() -> None:
    """cvsim.lab 顶层动词继续可用（re-export 源换到 dispatch，调用方无感）。"""
    import cvsim.lab as lab

    assert lab.run_circuit is not None
    assert lab.sample_circuit is not None
    assert "run_circuit" in lab.__all__ and "sample_circuit" in lab.__all__


# ---------------------------------------------------------------------------
# 3. ADR-0010 #8 结构守卫（AST，学 test_architecture.py）
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
RUNNER_MODULES = ("gaussian_backend", "fock_backend", "bosonic_backend")


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.level == 0:
                out.append(node.module)
            else:
                out.append(".".join(["cvsim.lab", node.module]))
    return out


def test_server_does_not_import_runners() -> None:
    """server.py 只经 dispatch 拿执行：不得 import 任何 runner 模块。"""
    mods = _imports(ROOT / "cvsim" / "lab" / "server.py")
    for runner in RUNNER_MODULES:
        assert not any(m == f"cvsim.lab.{runner}" for m in mods), (
            f"server.py imports {runner} directly — must go through dispatch (ADR-0010 #8)"
        )


def test_server_run_body_has_no_backend_branch() -> None:
    """/run /sample 路由体零 backend 特判（AST：函数体内无 backend 比较）。"""
    tree = ast.parse((ROOT / "cvsim" / "lab" / "server.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in ("run", "sample"):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Compare):
                    names = set()
                    for cmp_node in ast.walk(sub):
                        if isinstance(cmp_node, ast.Attribute) and cmp_node.attr == "backend":
                            names.add("backend")
                        if isinstance(cmp_node, ast.Constant) and cmp_node.value in (
                            "fock", "bosonic", "gaussian"
                        ):
                            names.add("lit")
                    assert not {"backend", "lit"} <= names, (
                        f"server.{node.name} branches on circuit.backend — "
                        "dispatch owns routing (ADR-0010)"
                    )


def test_ir_has_no_gaussian_execution_knowledge() -> None:
    """ir.py 无 gaussian 执行知识（ADR-0010 #3：_execute 搬去
    gaussian_backend 后 ir.py 只管 load/translate/schema）。"""
    src = (ROOT / "cvsim" / "lab" / "ir.py").read_text(encoding="utf-8")
    assert "GaussianState" not in src, (
        "ir.py must not reference GaussianState (execution knowledge)"
    )
    assert "_apply_measure" not in src, "ir.py must not own _apply_measure"
    assert "homodyne_mean" not in src, "ir.py must not import gaussian measurement ops"


# ---------------------------------------------------------------------------
# 4. check_wigner_mode 模板单点（ADR-0010 #5）：三个 runner 的越界消息字节一致
#    （模板与比较都在 cvsim.lab.ir.check_wigner_mode，backend 只保留调用点）
# ---------------------------------------------------------------------------

_WIGNER_OUT = "view.wigner_mode {mode} out of range (nmode={nmode})"


# ---------------------------------------------------------------------------
# 5. 分派零 backend 特判（§2.2）：路由体不得再长出 `if backend ==`
# ---------------------------------------------------------------------------

def test_dispatch_routing_has_no_backend_branch() -> None:
    """§2.2 回归守卫：dispatch 的路由函数体内不得比较 circuit.backend。

    原先三处特判（rng 派生、两处 steps 转发）让 ADR-0010 #1「一行一后端」
    失效 —— 接第四个后端要么被分支漏掉，要么得回来改本模块。差异现由
    ``_RUNNERS`` 行的 ``wants_rng`` 标志声明，路由体只剩查表 + 调用。

    AST 判据与 ``test_server_run_body_has_no_backend_branch`` 同型：
    函数体内同时出现 ``.backend`` 属性访问与后端名字面量 → 红。
    """
    tree = ast.parse((ROOT / "cvsim" / "lab" / "dispatch.py").read_text(encoding="utf-8"))
    routed = ("run_circuit", "sample_circuit", "_invoke")
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name in routed):
            continue
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Compare):
                continue
            names = set()
            for cmp_node in ast.walk(sub):
                if isinstance(cmp_node, ast.Attribute) and cmp_node.attr == "backend":
                    names.add("backend")
                if isinstance(cmp_node, ast.Constant) and cmp_node.value in (
                    "fock", "bosonic", "gaussian"
                ):
                    names.add("lit")
            if {"backend", "lit"} <= names:
                found.append(f"{node.name}:{sub.lineno}")
    assert not found, (
        f"dispatch 路由体又长出 backend 特判 {found} —— 差异应声明在 "
        f"_RUNNERS 行（ADR-0010 #1：新后端 = 一行，不改分派）"
    )


def test_runner_registry_rows_declare_rng_need() -> None:
    """注册表每行都带 wants_rng 标志，且与 runner 的真实 rng 语义一致。

    这条守的是**标志本身没说谎**：

    * gaussian 的 ``rng=None`` 是「均值路径」信号，不是「没给生成器」→ False；
    * bosonic 的 ``rng=None`` 会让测量层自造未播种生成器（同 seed 不可复现）
      → True，**这是真正承载行为的那个标志**（已变异验证：翻成 False 时
      ``test_bosonic_run_*`` 变红）；
    * fock → True 属**防御性声明**：``run_fock_circuit`` 内部已兜
      ``default_rng(circuit.seed)``，故这里翻成 False 不会改变可复现性
      （也已实测）。标志仍写 True，因为「由 dispatch 保证播种」是更清楚的分工。
    """
    from cvsim.lab import dispatch as d

    assert set(d._RUNNERS) == {"gaussian", "fock", "bosonic"}
    assert d._RUNNERS["gaussian"].wants_rng is False, (
        "gaussian 必须 wants_rng=False：rng=None 在它是「均值路径」而非「没给生成器」"
    )
    assert d._RUNNERS["bosonic"].wants_rng is True, (
        "bosonic 必须 wants_rng=True：它没有内部播种兜底，不派生即不可复现"
    )
    assert d._RUNNERS["fock"].wants_rng is True


def test_new_backend_row_needs_no_routing_change() -> None:
    """「一行一后端」是可执行声明：伪造第四后端只加一行即能跑通。

    若路由体仍有 backend 特判，这里会因未覆盖新 backend 而红 ——
    这正是该守卫要钉的性质（ADR-0010 后果段）。
    """
    from cvsim.lab import LabCircuit
    from cvsim.lab import dispatch as d

    calls: list[tuple] = []

    def fake_runner(circuit, rng, *, sampled=False, steps=False):
        calls.append((circuit.backend, rng, sampled, steps))
        return "ok"

    d._RUNNERS["quantum_dots"] = d._Runner(fake_runner, wants_rng=True)
    try:
        circuit = LabCircuit(backend="quantum_dots", seed=5)
        assert d.run_circuit(circuit) == "ok"
        assert d.sample_circuit(circuit) == "ok"
    finally:
        del d._RUNNERS["quantum_dots"]

    # both verbs reached the new row with a derived rng and no special-casing
    assert [c[0] for c in calls] == ["quantum_dots", "quantum_dots"]
    assert all(c[1] is not None for c in calls), "wants_rng=True 行必须收到派生 rng"
    assert [c[2] for c in calls] == [False, True], "sampled 标志按动词传递"


# ---------------------------------------------------------------------------
# 6. §2.2 行为等价：rng 语义逐后端钉住（重构未改物理）
# ---------------------------------------------------------------------------

def _gaussian_meas_body(seed: int = 7, **extra) -> dict:
    body = {
        "schema": "circuit_v1", "nmode": 1, "seed": seed,
        "ops": [
            {"id": "s", "op": "squeeze", "modes": [0], "params": {"r": 0.1, "phi": 0.0}},
            {"id": "m", "op": "measure_homodyne", "modes": [0], "params": {"name": "hd"}},
        ],
        "view": {"wigner_mode": 0, "lim": 4.0, "n": 16},
    }
    body.update(extra)
    return body


def test_gaussian_run_is_mean_path_but_sample_is_true_sampling() -> None:
    """gaussian：/run 走均值（可复现的确定值），/sample 必须真采样。

    这是 wants_rng=False 的**语义证明** —— 若 /run 也收到派生 rng，
    均值路径会变成随机采样，两者相等（本断言即红）。
    """
    from cvsim.lab import dispatch

    mean1 = dispatch.run_circuit(load_circuit(_gaussian_meas_body()))
    mean2 = dispatch.run_circuit(load_circuit(_gaussian_meas_body()))
    assert mean1.measured == mean2.measured, "/run 必须确定"
    assert mean1.measured[0]["outcome"] == 0.0, (
        "gaussian /run 的 homodyne 均值应为 0（rng=None → homodyne_mean）"
    )
    samp = dispatch.sample_circuit(load_circuit(_gaussian_meas_body()))
    assert samp.measured != mean1.measured, "gaussian /sample 必须真采样（≠ 均值）"


def test_bosonic_run_is_reproducible_per_seed() -> None:
    """bosonic：/run 必须同 seed 可复现 —— wants_rng=True 承载的就是这条。

    与 fock 不同，bosonic 没有内部播种兜底：``run_bosonic_circuit`` 直接把
    ``rng`` 交给 ``bc.run(rng=rng)``，而测量层的 ``rng is None`` 分支会自造
    一个**未播种**的 ``default_rng()``。故一旦把注册表里 bosonic 的
    ``wants_rng`` 翻成 False，本断言即红（已变异验证）。
    """
    from cvsim.lab import dispatch

    body = _v1_body("bosonic", initial=["gkp0"], ops=[
        {"id": "l", "op": "loss", "modes": [0], "params": {"T": 0.9}},
        {"id": "m", "op": "measure_homodyne", "modes": [0], "params": {"name": "hd"}},
    ])
    a = dispatch.run_circuit(load_circuit(body))
    b = dispatch.run_circuit(load_circuit(body))
    assert a.measured == b.measured, "bosonic /run 同 seed 必须可复现"


def test_fock_run_is_reproducible_per_seed() -> None:
    """fock：/run 也同 seed 可复现，但**不依赖** dispatch 派生。

    ``run_fock_circuit`` 自己兜了 ``default_rng(circuit.seed)``，故这条即使在
    ``wants_rng=False`` 下也成立 —— 它钉的是**可复现性这个结果**，
    不是 dispatch 的实现方式（后者由上面的标志断言负责）。
    """
    from cvsim.lab import dispatch

    body = _v1_body("fock", cutoff=4, ops=[
        {"id": "s", "op": "squeeze", "modes": [0], "params": {"r": 0.1}},
        {"id": "m", "op": "measure_homodyne", "modes": [0], "params": {"name": "hd"}},
    ])
    a = dispatch.run_circuit(load_circuit(body))
    b = dispatch.run_circuit(load_circuit(body))
    assert a.measured == b.measured, "fock /run 同 seed 必须可复现"


def test_explicit_rng_reaches_gaussian_sampling_path() -> None:
    """显式 rng 在 /sample 下必须送达 gaussian（测试注入通道）。

    显式 rng 与同 seed 派生生成器等价 —— 这条同时证明 _invoke 的
    「显式 rng 优先、不被 wants_rng=False 吞掉」分支是对的。
    """
    from cvsim.lab import dispatch

    derived = dispatch.sample_circuit(load_circuit(_gaussian_meas_body()))
    explicit = dispatch.sample_circuit(
        load_circuit(_gaussian_meas_body()), rng=np.random.default_rng(7)
    )
    assert explicit.measured == derived.measured, (
        "显式 rng(seed=7) 应与 circuit.seed=7 派生等价"
    )


def test_wigner_mode_guard_template_matches_all_backends() -> None:
    """同一越界输入 → 三 runner 同一消息（模板单点，422 文本可测）。"""
    from cvsim.lab import CircuitV0Error, dispatch

    views = {"wigner_mode": 3, "lim": 4.0, "n": 8}
    two_ops = [
        {"id": "s0", "op": "squeeze", "modes": [0], "params": {"r": 0.1}},
        {"id": "s1", "op": "squeeze", "modes": [1], "params": {"r": 0.1}},
    ]
    for backend, body in (
        ("gaussian", {**_gaussian_body(), "nmode": 2, "ops": two_ops, "view": views}),
        ("fock", _v1_body("fock", nmode=2, ops=two_ops, view=views, cutoff=4)),
        ("bosonic", _v1_body("bosonic", nmode=2, ops=two_ops, view=views, initial=[None, None])),
    ):
        circuit = load_circuit(body)
        with pytest.raises(CircuitV0Error) as ei:
            dispatch.run_circuit(circuit)
        assert str(ei.value) == _WIGNER_OUT.format(mode=3, nmode=2), f"{backend} drift"
