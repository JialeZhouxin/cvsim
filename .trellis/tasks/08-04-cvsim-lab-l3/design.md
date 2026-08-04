# Design — Gaussian Lab L3: Save/Load + Measure once

> 上游: `prd.md` D1–D9；保持 L2 vanilla JS、ordered-node IR、cvsim public API 边界。

## 1. 文件结构

```text
cvsim/lab/
  ir.py             # 修改：homodyne phi；mean/sample 双执行路径；RunResult
  server.py         # 修改：POST /sample；payload 增 seed / mode metadata
  static/
    index.html      # 修改：Save/Load、seed、Measure once、outcomes 区
    app.js          # 修改：run/sample 请求、条件态视图、文件 IO
    editor.js       # 修改：JSON seed/phi round-trip；Load 合法态替换入口
    ops.js          # 修改：homodyne 托盘/参数元数据
    style.css       # 修改：操作区、seed、measurement result 样式
  tests/
    test_lab_l3.py  # 新增：后端 sample、测量链、reproducibility、A5/A6 API
  tests/editor.test.mjs # 修改：homodyne phi、seed 与 round-trip 纯逻辑
```

不拆新服务、不加依赖。`ir.py` 继续拥有 circuit_v0 解析/执行；`server.py` 只做 HTTP 边界和 422 映射；前端继续三模块职责。

## 2. 数据流与契约

### `/run`（保持现状）

```text
JSON circuit_v0
  → load_circuit()
  → run_circuit(circuit)
  → mean-path GaussianState
  → RunResult
  → _payload()
  → Wigner + meters + measured metadata
```

`/run` 不读取 RNG；当前 heterodyne mean path、homodyne placeholder 语义保留为解析预览，除非现有 vision/测试要求把 mean metadata 补全。

### `/sample`

```text
JSON circuit_v0 + seed
  → load_circuit()
  → np.random.default_rng(seed)
  → sample_circuit(circuit, rng)
  → 按 nodes 顺序：
      homodyne: homodyne_sample_and_condition(state, mode, phi, rng)
      heterodyne: heterodyne_sample_and_condition(state, mode, rng)
      其他 op: 与 run path 相同
  → 最终条件 GaussianState
  → 相同 Wigner/meters builder
  → {schema, seed, sampled: true, measured[], nmode, rbar, V, wigner, meters}
```

单一执行核心建议：新增 `_execute(circuit, *, rng=None)`，`rng=None` 表示 `/run` mean path，传入 Generator 表示 sample path；不要在 `/run` 中创建 RNG。若为保持差异清晰而采用两个薄循环，也必须共享非测量 `_apply` 和 result builder，不复制物理公式。

### `measured[]` 条目

```json
{
  "op": "homodyne",
  "mode": 0,
  "phi": 0.0,
  "outcome": 0.123
}
```

```json
{
  "op": "heterodyne",
  "mode": 0,
  "outcome": [0.123, -0.456]
}
```

`mode` 是执行该节点时的运行时 mode；heterodyne 后续节点沿用 IR 的 ordered-node mode 语义和既有重映射规则。若现有 IR 只支持源后固定 mode，先以实际测试锁定，不额外引入连接图。

### Save/Load

- Save：`toCircuitJson(editor.getState())` → `JSON.stringify(payload, null, 2)` → `Blob` → `<a download="circuit_v0.json">`，不含 outcomes、条件态、meters。
- Load：`<input type=file accept="application/json,.json">` → `File.text()` → `JSON.parse` → `editor.loadJson(payload)`；先验证 `schema`、nodes、view、seed、homodyne phi，再替换 state；失败只调用 `onStatus(error, false)`，不改合法 state。
- Load 成功：`editor.render()` → `onRun(payload)`；清除 sample view。

## 3. 后端边界

### `ir.py`

公开内部接口（模块级即可，不新增 public package API）：

```python
def run_circuit(circuit: CircuitV0) -> RunResult: ...
def sample_circuit(circuit: CircuitV0, rng: np.random.Generator) -> RunResult: ...
```

或等价的：

```python
def run_circuit(circuit: CircuitV0, *, rng: np.random.Generator | None = None) -> RunResult: ...
```

必须满足：

- `rng is None`: mean path，无 RNG；`/run` 输出稳定
- `rng` 非 None: 所有测量节点都抽样；非测量节点不消耗随机数
- homodyne：读取 `phi`（缺省 `0.0`），采样 + condition，mode 保留
- heterodyne：采样 + condition，mode 移除
- 后测量使用当前 `state` 和当前 mode
- `RunResult` 的 `measured` 有序

共享 `_result(state, view, measured)` 生成 Wigner/meters。`wigner_mode` 超出条件态 nmode 时，沿用 422，而不是静默改 mode。

### `server.py`

```python
@app.post("/sample")
def sample(body: dict[str, Any]) -> dict[str, Any]:
    circuit = load_circuit(body)
    seed = circuit.seed
    result = sample_circuit(circuit, np.random.default_rng(seed))
    return _payload(result, seed=seed, sampled=True)
```

保留现有异常边界：`CircuitV0Error` / `ValueError` → HTTP 422；不捕获 broad `Exception`。`_payload` 可选参数保持 `/run` 兼容。

## 4. 前端组件

### `index.html`

在已有 editor action/header 旁加入：

- `button#save-btn`：下载当前 `circuit_v0`
- `input#load-input[type=file][accept=".json,application/json"]`
- `input#seed-input[type=number]`：整数；默认取 JSON `seed`
- `button#sample-btn`：Measure once
- `section#measurement-result`：seed、outcomes；默认隐藏

homodyne 已在白名单但 L2 托盘未展示；L3 加入托盘，与 `ops.js` 元数据一致。其 `phi` 参数默认 0，范围 `[0, 2π]`。

### `app.js`

- `doRun` 成功：`render(body, ...)`，清除 `sampled`/outcome panel，状态回解析视图。
- `doSample`：从 editor 当前 state 序列化，取 seed input，构造 payload；请求 `/sample`；响应序号守卫与 `doRun` 相同；成功 `render(body, ...)` + 显示 seed/outcomes + 标记条件态视图。
- 参数变更、mode 改动、手动 Run：清除条件态视图；参数变更继续 debounce 120ms。
- 保存不调用后端；加载成功才调用 `/run`。
- 禁用按钮只覆盖当前请求，错误恢复不污染旧结果。

### `editor.js` / `ops.js`

- `OPS.homodyne` 加入可见 palette：`kind: single, params: {phi: {min: 0, max: TAU, step: 0.01, def: 0}}`。
- `toCircuitJson` 保留顶层 `seed`；`stateFromJson` 接受整数 seed、homodyne 可选 `phi`。
- `loadJson(payload)` 是纯校验后替换入口；失败返回 `{error}` 或抛出项目现有约定的 UI-safe error，不半更新 state。

## 5. 错误处理

| 场景 | 后端 | 前端 |
|---|---|---|
| body/schema/nodes/seed/phi 非法 | 422 `detail` | 红色 status，不替换现有电路 |
| mode 因 heterodyne 后失效 | 422 | 保留旧条件态，显示 detail |
| Wigner 条件态数值失败 | 422 | 显示错误，不假造图 |
| 文件 JSON 解析失败 | 不请求后端 | 红色 status，当前电路不变 |
| 同 seed | 200，逐项一致 | 正常显示 outcome + seed |

## 6. 测试设计

### 后端 `tests/test_lab_l3.py`

使用现有 FastAPI TestClient/pytest 模式；不引入新库。

1. `test_sample_repeats_same_seed`: TMSV + heterodyne；两次 `/sample` body 相同，比较 `measured`, `rbar`, `V`。
2. `test_sample_measurement_order_and_condition_chain`: homodyne → heterodyne；`measured[0].op == homodyne`、`measured[1].op == heterodyne`，两 outcome 类型正确，第二步在第一步条件态上执行。
3. `test_homodyne_keeps_mode_and_heterodyne_removes_mode`: 单 homodyne `nmode` 不变；单 heterodyne `nmode` 减一。
4. `test_sample_phi_changes_homodyne_variance`: squeezed state，`phi=0` 与 `phi=π/2` 多 seed 统计方差符合物理趋势/解析方差。
5. `test_run_remains_deterministic_and_sample_is_separate`: 两次 `/run` 完全一致；`/sample` 后 `/run` 仍一致。
6. `test_sample_invalid_seed_or_payload_returns_422`: API 错误映射。
7. `test_load_homodyne_phi_default_and_round_trip`: 缺 phi 默认为 0；显式 phi 保留。

测试避免精确断言不同 seed 一定不同，只断言同 seed 可复现；统计测试使用足够 shots/宽容度，或直接检查 `homodyne_sample` 的已知方差路径。

### 前端 `tests/editor.test.mjs`

1. homodyne metadata 存在且 `phi` 默认 0；`toCircuitJson` 保留 phi。
2. state → JSON → state 保留 `seed`、nodes、view。
3. 非法 schema/seed/phi 返回错误且不修改旧 state（通过纯函数返回值验证）。

### 手工验收

- 冷启动 → L2 主剧本 → 添加 homodyne → Measure once，看到 `outcome`、`seed`、条件态 Wigner。
- 同 seed 重测结果一致；改 seed 结果通常变化。
- Save 下载；刷新；Load 上传；拓扑、参数、meters 恢复。

## 7. 版本/文档

- `docs/vision-gaussian-lab-ui.md` changelog 增加 `0.5.0`：L3 Save/Load + homodyne/heterodyne sample，测试数与运行命令按实际结果填写。
- 不修改 simulator theory notes，不新增量子库依赖。
