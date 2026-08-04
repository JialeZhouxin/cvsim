# Implement — Gaussian Lab L3

> 上游: `design.md`。每步验证后进下一步。TDD：先写失败测试，再实现。

## 关键物理事实（已实验验证）

- homodyne 条件态 **V 奇异**（`det(2V)=0`）：`wigner_grid` raise、`purity` raise、`mean_photon` 可算但可能无意义（如负值）。
- partial_trace 到**未测 mode** 后 V 正定 → Wigner 可画（TMSV 测 mode0，keep=[1] 正常）。
- heterodyne 删模，条件态正常。
- 因此：Wigner 视图若落在"homodyne 测向 mode"→ 显示"理想本征态，无有限 Wigner"，**不伪造数据**。

## S1: 后端 IR — 双执行路径（TDD）

**文件**: `cvsim/lab/ir.py`、`tests/test_lab_ir.py`（+ 新 `tests/test_lab_l3.py`）

### 1a. homodyne phi 参数

- [ ] **Step 1 写失败测试**（`tests/test_lab_l3.py`）:
  - `test_load_homodyne_phi_default_zero`: `{"op":"homodyne","mode":0,"params":{}}` → `load_circuit` 后节点 params 无 phi 可运行（mean path 不炸）
  - `test_load_homodyne_phi_kept`: `params:{"phi":1.5}` → round-trip 保留 1.5
- [ ] **Step 2 跑测试**：当前 `_apply` homodyne 分支忽略 phi，两测试应通过或暴露缺参数校验 → 记录实际失败
- [ ] **Step 3 实现**：`_apply` homodyne 分支：
  ```python
  if op == "homodyne":
      phi = _num(p.get("phi", 0.0), where, "phi")
      mu = homodyne_mean(state, mode, phi)
      entry = {"op": "homodyne", "mode": mode, "phi": phi, "outcome": mu}
      return state, entry   # mean path 不 condition、不删模（保留 L0 语义）
  ```
  导入 `homodyne_mean`（ir.py 顶部 import 列表）。
- [ ] **Step 4 跑测试绿**；`python -m pytest tests/test_lab_l3.py tests/test_lab_ir.py -q`

### 1b. sample_circuit 执行核心

- [ ] **Step 5 写失败测试**:
  - `test_sample_heterodyne_removes_mode`: TMSV+heterodyne，`sample_circuit(c, rng)` → `measured[0].op=="heterodyne"`，outcome 为 `[re, im]` 列表，最终 nmode=1
  - `test_sample_homodyne_keeps_mode`: TMSV+homodyne → nmode=2，outcome 为 float
  - `test_sample_same_seed_reproducible`: 同 circuit 同 seed 两次 → `measured` 与 `rbar` 全等（`np.allclose`）
  - `test_sample_multi_measurement_chain`: homodyne(mode0) → heterodyne(mode1) → `measured` 长度 2、顺序正确、第二条在第一条条件态上执行（heterodyne 后 nmode 1）
  - `test_run_no_rng_deterministic`: 两次 `run_circuit` 完全一致；`/sample` 不影响
- [ ] **Step 6 跑测试**：`sample_circuit` 不存在 → 失败（ImportError）
- [ ] **Step 7 实现**：`ir.py` 重构为共享执行核心：
  ```python
  def _execute(circuit: CircuitV0, *, rng: np.random.Generator | None = None) -> RunResult:
      state = None
      measured = []
      for node in circuit.nodes:
          if node.op in SOURCE_OPS:
              ...  # 与现状相同
          else:
              state, entry = _apply(node, state, rng=rng)  # 见 1c
              if entry is not None:
                  measured.append(entry)
      return _build_result(state, circuit.view, measured)

  def run_circuit(circuit: CircuitV0) -> RunResult:
      return _execute(circuit, rng=None)

  def sample_circuit(circuit: CircuitV0, rng: np.random.Generator) -> RunResult:
      return _execute(circuit, rng=rng)
  ```
  `_build_result` = 原 `run_circuit` 尾部（wigner/meters 组装），但加奇异处理（见 1d）。
  **注意**：仅当 wigner 视图 mode 落在奇异 homodyne mode 时才影响结果组装；`rng=None` 路径输出与 L2 完全一致（回归：`tests/test_lab_api.py::test_run_main_scene` 必须绿）。
- [ ] **Step 8 跑测试绿**

### 1c. _apply 测量分支（rng 感知）

- [ ] **Step 9 实现**（含测试在 1b 已写）:
  ```python
  def _apply(node, state, *, rng=None):
      ...
      if op == "homodyne":
          phi = _num(p.get("phi", 0.0), where, "phi")
          if rng is None:
              mu = homodyne_mean(state, mode, phi)
              return state, {"op": "homodyne", "mode": mode, "phi": phi, "outcome": mu}
          o, st = homodyne_sample_and_condition(state, mode, phi, rng=rng)
          return st, {"op": "homodyne", "mode": mode, "phi": phi, "outcome": o}
      if op == "heterodyne":
          if rng is None:
              outcome = heterodyne_mean(state, mode)
              st = heterodyne_condition(state, mode, outcome)
              return st, {"op": "heterodyne", "mode": mode, "outcome": [outcome.real, outcome.imag]}
          beta, st = heterodyne_sample_and_condition(state, mode, rng=rng)
          return st, {"op": "heterodyne", "mode": mode, "outcome": [beta.real, beta.imag]}
  ```
  导入 `homodyne_mean`, `homodyne_sample_and_condition`, `heterodyne_sample_and_condition`。
- [ ] **Step 10 跑测试绿**

### 1d. 奇异 Wigner/meters 处理

- [ ] **Step 11 写失败测试**:
  - `test_sample_homodyne_singular_view_mode`: TMSV r=0.6 + homodyne(mode0)，view.wigner_mode=0 → 响应（或 `_build_result`）不 raise；`wigner is None`；`meters["singular"]` 标记；`nmode=2`
  - `test_sample_homodyne_other_mode_wigner_ok`: 同上 view.wigner_mode=1 → wigner 正常（grid 形状 (64,64)）
  - `test_sample_heterodyne_view_mode_valid`: TMSV+heterodyne → nmode=1，wigner_mode=0 正常
- [ ] **Step 12 跑测试失败**
- [ ] **Step 13 实现**：`_build_result`:
  ```python
  wigner = None
  singular = False
  try:
      keep = partial_trace(state, keep=[view.wigner_mode])
      X, P, W = wigner_grid(keep, lim=view.lim, n=view.n)
      wigner = (X, P, W)
  except ValueError as e:        # det(2V) <= 0 → 奇异 homodyne 条件态
      singular = True            # 不吞其他错误：仅 det 类（可加 e 匹配）
  meters = _meters(state)        # 现有逻辑；purity 奇异时除零
  ```
  关键问题：`purity` 对奇异 V raise。**决策**：`_meters` 中 purity/log_neg 包 try，失败置 `None`，成功照旧；`mean_photon` 保留（有定义，负值也诚实显示）。`meters["singular"] = singular`。
  **注意**：`run_circuit`（mean path）不会产生奇异态（heterodyne mean 条件态正常），奇异分支只影响 sample path；`/run` 回归测试必须仍绿。
- [ ] **Step 14 跑测试绿**；全套 `python -m pytest tests/ -q` + `ruff check cvsim/`

## S2: 后端 server — POST /sample（TDD）

**文件**: `cvsim/lab/server.py`、`tests/test_lab_api.py`

- [ ] **Step 15 写失败测试**:
  ```python
  def test_sample_endpoint_reproduces_same_seed():
      body = {...TMSV+heterodyne, "seed": 7...}
      r1 = client.post("/sample", json=body)
      r2 = client.post("/sample", json=body)
      assert r1.status_code == 200 and r2.status_code == 200
      assert r1.json()["measured"] == r2.json()["measured"]
      assert r1.json()["seed"] == 7
      assert r1.json()["sampled"] is True

  def test_sample_endpoint_422_bad_seed(): seed="x" → 422
  ```
- [ ] **Step 16 跑测试失败**（404）
- [ ] **Step 17 实现**:
  ```python
  @app.post("/sample")
  def sample(body: dict[str, Any]) -> dict[str, Any]:
      try:
          circuit = load_circuit(body)
          result = sample_circuit(circuit, np.random.default_rng(circuit.seed))
      except (CircuitV0Error, ValueError) as e:
          raise HTTPException(status_code=422, detail=str(e)) from e
      return _payload(result, seed=circuit.seed, sampled=True)
  ```
  `_payload` 加可选参数 `seed=None, sampled=False`：`seed` 写入顶层；`sampled` 写入顶层；wigner 为 None 时 `"wigner": None`。
  顶层加 `"singular": result.meters.get("singular", False)`（或放 meters 内，前端一致即可）。
- [ ] **Step 18 跑测试绿**；`/run` 现有测试回归绿

## S3: 前端 ops/editor — homodyne + seed（TDD）

**文件**: `cvsim/lab/static/ops.js`、`cvsim/lab/static/editor.js`、`tests/editor.test.mjs`

- [ ] **Step 19 写失败测试**（`tests/editor.test.mjs`）:
  - homodyne 在 OPS 且 `params.phi.def === 0`、`params.phi.max === TAU`
  - `toCircuitJson(state)` 保留 `seed`（`{...state, seed: 42}` → 输出 `seed: 42`）
  - `stateFromJson` 接受 `seed: 7` 与 homodyne `params: {phi: 1.5}`
- [ ] **Step 20 跑测试失败**（homodyne 缺失、seed 硬编码 0）
- [ ] **Step 21 实现**:
  - `ops.js`: `OPS.homodyne = { label: "零差测量", kind: "single", params: { phi: { min: 0, max: TAU, step: 0.01, def: 0 } } };`（8→9 op）
  - `editor.js`: `defaultState()` 加 `seed: 0`；`stateFromJson` 校验 `seed`（整数 ≥0，非法报错）；`toCircuitJson` 输出 `state.seed`
  - `editor.js` 加 `export function loadJson(state, payload)`: 调 `stateFromJson(payload)`；成功返回 `{state}`，失败返回 `{error}`，**不改** `state`（纯函数，可 node 测试）
- [ ] **Step 22 跑测试绿**：`node --test tests/editor.test.mjs`

## S4: 前端 app/index — Save/Load + Measure once

**文件**: `cvsim/lab/static/index.html`、`cvsim/lab/static/app.js`、`cvsim/lab/static/style.css`、`tests/test_lab_ui.py`

- [ ] **Step 23 HTML**: `.panel__actions`（电路序列区）加：
  ```html
  <button id="save-btn" type="button" class="btn btn--ghost">保存 JSON</button>
  <label class="btn btn--ghost" for="load-input">载入 JSON<input id="load-input" type="file" accept=".json,application/json" class="sr-only"></label>
  <label class="hint" for="seed-input">seed</label>
  <input id="seed-input" type="number" min="0" step="1" class="input mono" value="0">
  <button id="sample-btn" type="button" class="btn btn--primary">Measure once</button>
  ```
  结果区加 `#measurement-panel`（默认 hidden）：`<div id="measurement-panel" class="measurement" hidden>` — seed 显示 + outcomes 列表（`measured` 每项：op/mode/outcome 文本）+ "奇异条件态"提示（`singular` 时显示"理想本征态，无有限 Wigner"）。
- [ ] **Step 24 app.js**:
  - `doSample()`：镜像 `doRun`（seq 守卫、setBusy、错误红条）；payload = `toCircuitJson(editor.getState())` + `view.wigner_mode` + `seed: Number(seedInput.value)`；`fetch("/sample", ...)`；成功 `render(body)` + 显示 measurement panel（outcomes、seed、singular 提示）
  - `render()` 处理 `wigner === null`：清空 canvas + 热图区显示提示（不炸）
  - Save：`Blob` + `<a download>`（文件名 `circuit_v0.json`）
  - Load：`input.files[0].text()` → `JSON.parse` → `editor.loadJson`；`error` → 红条，不动当前电路；成功 → `editor.render()` + `doRun(payload)` + 隐藏 measurement panel
  - 手动 Run / 参数变更 / mode 变更 / Load：隐藏 measurement panel（回解析视图）
  - 文件未选 / 解析失败：`setStatus("载入失败: ...", false)`
- [ ] **Step 25 UI 测试**（`tests/test_lab_ui.py` 或现有模式）：headless 无 console error；`#save-btn`/`#sample-btn`/`#seed-input` 存在
- [ ] **Step 26 跑全部测试**: `python -m pytest tests/ -q` + `ruff check cvsim/` + `node --test tests/editor.test.mjs`

## S5: 手工验收 + 收尾

- [ ] **Step 27 手工主剧本扩展**（用户）:
  1. 主剧本 1–6（L2 回归）
  2. 拖 homodyne → Measure once → 看到 outcome + seed；同 seed 再点 → 结果一致；改 seed → 通常不同
  3. homodyne 后被测 mode 热图区显示"理想本征态"提示；另一 mode Wigner 正常
  4. 拖 heterodyne → Measure once → nmode 减一、outcome 复数
  5. 多测量：homodyne+heterodyne 顺序条件链
  6. Save JSON → 刷新 → Load → 拓扑/参数/meters 一致（A5）
  7. Load 坏文件 → 红条报错，电路不变
- [ ] **Step 28 A6 自动化验证**：`tests/test_lab_l3.py` 覆盖（已 S1/S2 写）
- [ ] **Step 29 vision changelog**：`docs/vision-gaussian-lab-ui.md` §14 加 `0.5.0` 条目（L3 landed：Save/Load + /sample + homodyne；测试数按实际；标注 singular 视图语义）
- [ ] **Step 30 收尾**：全套测试绿 → commit（`feat(lab): Gaussian Lab L3 — Save/Load + Measure once`）→ OCR review → archive `08-04-cvsim-lab-l3`

## 不做清单

- ❌ 抽样写回 JSON / 实验记录文件；localStorage
- ❌ undo、扫参（L4）、amplifier/MZ 新 op
- ❌ batch sampling、多 shot 统计
- ❌ 奇异态的 Wigner 正则化伪造（显示"理想本征态"提示，不造数）
- ❌ 模拟器 Phase 3 compile/serialize（L3 只探路 Save/Load 格式）
