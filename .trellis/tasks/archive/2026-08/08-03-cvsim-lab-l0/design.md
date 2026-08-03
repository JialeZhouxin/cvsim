# Design — Gaussian Lab L0

> 上游: `prd.md`；约束来源: `docs/vision-gaussian-lab-ui.md` §6/§7/§8

## 1. 包结构

```
cvsim/
  lab/                    # 新子包；cvsim 核心不依赖它
    __init__.py           # 导出 CircuitV0Error, RunResult, run_circuit, load_circuit
    ir.py                 # circuit_v0 schema dataclass + 验证 + 编译执行引擎（无 fastapi 依赖）
    server.py             # FastAPI app（/run, /health）；import fastapi 仅在此
tests/
  test_lab_ir.py          # schema 验证表 + golden 等价（A9）
  test_lab_api.py         # TestClient 端到端 + A8 private-import 守卫 + A4 Wigner(vacuum)
```

**依赖策略**: `pyproject.toml` 加 optional extra `lab = ["fastapi>=0.110", "uvicorn>=0.27"]`；`httpx` 入 `dev` extra（TestClient 需要）。核心依赖 numpy/scipy 不动。

## 2. `circuit_v0` schema（ir.py）

```python
@dataclass
class Node:
    id: str                 # 非空
    op: str                 # 白名单枚举
    params: dict[str, Any]  # op 专属，见 §3
    mode: int | None = None     # 单模 op
    modes: list[int] | None = None  # 多模 op

@dataclass
class CircuitV0:
    schema: str = "circuit_v0"   # 版本字段；其他值 → 拒绝
    seed: int = 0                # L0 保留不用（无抽样）；纯记录
    nodes: list[Node] = ...
    edges: list[Any] = ...       # L0 保留、后端忽略（vision §7.5: ui/边不参与物理）
    view: View = View(wigner_mode=0, lim=5.0, n=64)
    ui: dict = field(default_factory=dict)  # 后端忽略

@dataclass
class View:
    wigner_mode: int = 0
    lim: float = 5.0
    n: int = 64
```

- `load_circuit(data: dict) -> CircuitV0`：字段/类型校验，非法抛 `CircuitV0Error(reason)`（消息给 UI 用）
- `circuit_v0` 语义: **nodes 数组顺序 = 执行顺序**；mode/modes 是**执行时点**的运行时模号（heterodyne 删模后，后续指令按删模后索引解释）。edges 不参与执行（vision §7 sketch 中 edges 即空）。
- 禁止隐式全局模号：每个 op 必须有 mode 或 modes，缺 → 错误。

## 3. op → 执行映射（全部走 public API）

| op | 参数 | 执行 |
|----|------|------|
| `vacuum` | `nmode:int=1` | `GaussianState.vacuum(nmode)`；要求是首指令 |
| `coherent` | `alpha:complex` | `GaussianState.coherent(alpha)`；要求是首指令 |
| `tmsv` | `r:float` | `GaussianState.tmsv(r)`；要求是首指令 |
| `squeeze` | `r, phi=0` | `squeeze(st, r, mode, phi)` |
| `displace` | `alpha` | `displace(st, alpha, mode)` |
| `phase` | `phi` | `phase(st, phi, mode)` |
| `fourier` | — | `fourier(st, mode)` |
| `beamsplitter` | `theta, phi=0` | `beamsplitter(st, m1, m2, theta, phi)`；`modes` 必须恰 2 个 |
| `two_mode_squeeze` | `r` | `two_mode_squeeze(st, r, m1, m2)`；`modes` 恰 2 个 |
| `loss` | `T, nbar=0` | `loss(st, T, mode, nbar)` |
| `homodyne` | `phi=0` | 模拟器语义：**不删模**。返回空 outcome 占位；状态不删模。v0 无抽样，outcome 不改变态 |
| `heterodyne` | — | `heterodyne_condition(st, mode, outcome)` 的**均值路径**：outcome = `heterodyne_mean(st, mode)`；condition 后**删模**（api-stability §5） |

参数校验（数值边界）复用 cvsim 自身异常（`loss` 的 T∈[0,1] 等）；执行期异常包成 `CircuitV0Error`。

## 4. 执行引擎

```python
def run_circuit(circuit: CircuitV0) -> RunResult:
    # 1) 遍历 nodes：source 必须首位；其余要求已存在 state；mode 范围检查
    # 2) heterodyne: state = heterodyne_condition(state, mode, heterodyne_mean(state, mode))
    # 3) 终态 → view 校验 wigner_mode < state.nmode
    # 4) wigner = wigner_grid(partial_trace(state, keep=[view.wigner_mode]), lim, n)
    # 5) meters: purity(state), mean_photon(state)（逐模数组）, 
    #    log_negativity(state)（nmode≥2 时）
```

`RunResult` dataclass: `nmode, rbar(np), V(np), wigner=(X,P,W), meters=dict, measured=[]`（L0 measured 空列表占位）。

**view 重映射语义**: `wigner_mode` 基于**最终**（删模后）模号。heterodyne 后想 view 剩余模 → 前端传删模后的索引。PRD 验收第 4 条即覆盖此。

## 5. FastAPI 后端（server.py）

| 端点 | 行为 |
|------|------|
| `GET /health` | `{"status":"ok","schema":"circuit_v0","cvsim":版本}` |
| `POST /run` | body = circuit_v0 dict → 校验（422 + 原因）→ `run_circuit` → JSON |
| `POST /sample` | **不建**（L3） |

JSON 编码: `rbar/V` 转 list；W 转 list of list。响应顶层: `{schema, nmode, rbar, V, wigner:{x,p,W}, meters, measured}`。

## 6. 测试

- `test_lab_ir.py`:
  - schema 验证表: 非法 op / 缺 mode / 非法 view / 坏 schema 版本 → `CircuitV0Error`
  - **golden 等价 (A9)**: fixture JSON（tmsv 0.6 → loss 0.8×2 → bs θ=π/4）的 `V,rbar` == 手写 `GaussianState` 链 (atol 1e-10)
  - heterodyne 删模: JSON（tmsv → heterodyne m0）→ 1 模终态 == 手写 `heterodyne_condition` (atol)
  - homodyne 不删模: nmode 保持
  - wigner_mode 重映射: heterodyne 后 view 剩余模索引
- `test_lab_api.py`:
  - `/health` 200
  - `/run` 主剧本 JSON → 200 + wigner 形状 (n,n) + meters 有 purity
  - 非法 op → 422 + 原因
  - **A4**: vacuum → W 中心 == `wigner_grid(GaussianState.vacuum(), ...)` 直调
  - **A8 守卫**: 读 `cvsim/lab/*.py` 源码，断言无 `gaussian._` / `from cvsim.fock` / `from cvsim.bosonic` import

## 7. 关键决策记录

| # | 决策 | 理由 |
|---|------|------|
| D1 | nodes 顺序执行，edges 后端忽略 | vision sketch edges 空；L0 无图求值，L2 拖拽时 edges 才承担拓扑 |
| D2 | heterodyne 用均值路径（`heterodyne_mean` 作 outcome） | v0 无抽样（L3 才有 seed/sample）；仪表可复现；L3 换真抽样不破坏 schema |
| D3 | homodyne 不删模 | 与模拟器 `homodyne_condition` 语义一致（vision §4.4） |
| D4 | `cvsim/lab` 独立子包 + optional extra | 核心依赖不膨胀；A8 边界在 server.py 单点收口 |
| D5 | 运行态模号重映射 | 唯一满足"测后少模 + 显式模号"的简单语义 |
