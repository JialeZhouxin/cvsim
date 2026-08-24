# Bosonic B6 GUI 三件套——技术设计

## 1. 数据流总览

```
GKP QEC JSON (backend="bosonic", initial=["gkp0","gkp1"])
  → load_circuit: _load_bosonic (whitelist + bosonic IR validate)
  → RunResult path: run_bosonic_circuit(circuit, rng=default_rng(seed), steps=...)
      BosonicCircuit.from_ir(raw) → 含 initial 初态
      → compile().run() → (final_state, results)
      → Wigner(final) + meters + measured
  → /fidelity: sweep γ → per-point rebuild + run → pure_fidelity(data-mode, gkp0)
  → 前端: palette(ops.js backends+=bosonic) + initial 卡 + Wigner step slider + curve
```

## 2. IR `initial` 字段（R1）

- **编码**: `initial: ["gkp0", "gkp1"]` — per-mode 态名列表，`null`/缺省 = 真空。**List[null|"gkp0"|"gkp1"]**。
- **入口**: bosonic `ir.py` validator 保持忽略（`EXTENSION_FIELDS` 已有 initial，R1 只把"忽略"变"消费"）；**`BosonicCircuit.from_ir`** 读 `data.get("initial")`：
  ```python
  initial = data.get("initial")
  if initial is not None:
      if not isinstance(initial, list) or not 1 <= len(initial) <= nmode:
          raise ValueError(...)
      for item in initial:
          if item is not None and item not in {"gkp0", "gkp1"}:
              raise ValueError(f"initial: 未知态源 {item!r}")
  circuit = BosonicCircuit(nmode, initial=initial)
  ```
- **缺省**: 无字段/全 None → 真空（B5 行为，旧 JSON 零破坏）。
- **roundtrip**: `to_ir` 回写 initial（`_ops` 之外存 `self._initial` 元数据）。

## 3. `BosonicCircuit(initial)` + 初态拼接（R1/R2）

- 构造: `BosonicCircuit(nmode, initial: list[str|None] | None = None)`。
- 态源解析: `None→vacuum(1)`，`"gkp0"→gkp0()`，`"gkp1"→gkp1()`（均为 1-mode `BosonicState`）。
- **张量拼接**（新内部 helper，state.py 或 circuit.py）: per-mode 组件直积
  ```
  K = Π_k K_k; V_k = blockdiag(V_k^0, V_k^1, ...); r̄_k = concat; w_k = Π w
  ```
  （mode 补真空 I/2；与 Fock F7 `initial` per-mode 语义对齐，只是态名而非数态）。
- **K=1 恒定锁不破**: initial 在 compile 之前给出初态；gate/通道/测量仍不改分量数。
- `run(initial=...)` 覆盖参数可选（对齐 Gaussian run(values) 模式）。

## 4. `pure_fidelity` 双 V 升级（R3）

- **新内核**（`cvsim/bosonic/gkp.py` `_gauss_overlap` 或分析模块内）:
  ```python
  def gauss_overlap_two_V(Va, Vb, r_i, r_j, m=1):
      # S = 2^m · (detVa·detVb)^{1/4} / √det(Va+Vb)
      #     · exp(−¼ Δrᵀ (Va+Vb)⁻¹ Δr)
  ```
- **推导已验证**: 等 V=V0 → `exp(−⅛ΔrᵀV0⁻¹Δr)` ≡ 现 B4 内核（无 det 因子残留）→ **B4 layer-2 测试原样绿**。
- **pure_fidelity**（analyse.py）: 去"等 V ValueError"，`T[i,j] = _gauss_overlap(V_i^a, V_j^b, r_i, r_j)`（per-component V）。实中心；复数中心 `ValueError` 留 B7。
- `gkp.py` 内部 Gram 调用（同态等 V）传 `Va=Vb`，保持等 V 路径。
- **GKP QEC 物理**: loss γ 缩 data V → 双 V fidelity 真实反映有损纠错保真度随 γ 单调降。

## 5. Fidelity sweep（R4，A 项）

- **新端点 `/fidelity`**（不复用纯函数 `/scan`，因 sweep 有 RNG）:
  ```json
  { ...circuit (bosonic, 含 initial)..., "target": {"mode": 0, "state": "gkp0"},
    "sweep": {"node_id": "...", "param": "T", "min": 1.0, "max": 0.5, "n": 21},
    "seed": 0, "rounds": 1, "view": {wigner_mode: 0, ...} }
  ```
- **每点**: `BosonicCircuit.from_ir(改参 JSON)` → `compile().run(rng=default_rng(seed))` → 取 target mode 0 后态 → `pure_fidelity(post, gkp0())`。
- **rounds=N**: 多 seed（`default_rng(seed+i)`）平均 → 平滑曲线。
- **响应**: `{"xs": [γ...], "t": [fidelity...]}`, γ = 1−T（loss 节点 T↔γ 语义，前端标 ρ 或 γ 由 UI 显示）。
- **无 S 曲线目标配置**: GKP QEC 教学 target 固定 = mode0 gkp0（R2 剧本）。

## 6. Step execution（R5，C 项）

- **`/run` body 加 `"detail": "steps"`**（bosonic 路径）→ 响应加 `"steps": [...]`:
  ```json
  {"steps": [
    {"step": 0, "op": "cz",        "nmode": 2, "meters": {"purity":..,"mean_photon":..}, "wigner": {...}},
    {"step": 1, "op": "loss",      "nmode": 2, ...},
    {"step": 2, "op": "homodyne",  "nmode": 1, ...},
    {"step": 3, "op": "displace",  "nmode": 1, ...}],
    ...最终态}
  ```
- **实现**: `BosonicCircuit.compiled` 暴露 break-point 段序（通道/测量位于段边界）+ `CompiledBosonic` 提供"跑至第 k 段"中间态；或直接复用 `compile().run()` 的分段执行内部循环，逐段收集 `(op, state)` 快照。
- **wigner**: 每步 `state.nmode==1` 直接 `wigner_grid`；选 `view.wigner_mode` 的约化 → 多模态用段 helper（删非目标 mode，逐分量 partial trace，复制 B5 `remove_mode` 实现保留单模）。
- **meters**: `purity` + `mean_photon`（B4/B1 现成）。
- 无测量电路 `detail="steps"` → steps = 门段（通道也是 break point）。

## 7. Lab 路由解锁（R6）

- **`cvsim/lab/ir.py`**:
  - `BOSONIC_WHITELIST = {squeeze,displace,phase,fourier,beamsplitter,two_mode_squeeze,mach_zehnder,cz,cx,interferometer,loss,amplifier,phase_noise,gaussian_channel,measure_homodyne,measure_heterodyne,measure_threshold}`。
  - `_load_bosonic(data, seed, view, ui)`（mirror `_load_fock`，raw 持证，core=None）。
  - `run_bosonic_circuit(circuit, rng, steps=False) -> dict`（JSON payload：nmode/cutoffs[w=None]/wigner/dist/meters/measured[+steps]）。
  - `validate_bosonic_ir` 供 whitelist 后校验。
- **`cvsim/lab/server.py`**: `/run` `/sample` 加 bosonic 分支（`run_bosonic_circuit` + seed 确定性）；`/scan` bosonic → 422（E_N 不做）；`/fidelity` 新端点（bosonic-only，Gaussian/Fock → 422）。
- **`cvsim/lab/__init__.py`**: 导出 `run_bosonic_circuit` + `fidelity_sweep`。

## 8. 前端三件套（R7）

- **`ops.js`**: 各 op `backends` 数组加 `"bosonic"`（11 门 + 3 通道 + 3 测量 + cz/cx/interferometer）；`initial` 卡（view 中 mode 选 gkp0/gkp1/真空）。
- **`index.html` + `app.js`**: backend 切换三角（已 Fock 有）；bosonic 结果面板 = Wigner evolution view（步进滑条 + 单模热图 froz）+ fidelity sweep curve（`/fidelity` 拉取渲染）+ step 播放。
- **`ops.js`/`app.js` 结构**: bosonic 面板复用 fock.js 的离散渲染路径（fock.js 已示范 palette/panel per-backend 分表）——新增 `bosonic.js` 或扩 ops.js 元数据。
- **旧 JSON**: backend 缺省 gaussian → 前端/后端零破坏（exit 3）。

## 9. 兼容性 / 回滚

- 旧 Gaussian/Fock JSON：`initial` 不出现（bosonic-only 消费）；`detail` 参数不在 Gaussian 路径消费 → 零破坏。
- `pure_fidelity` 签名兼容（两参不变），仅内部内核升级 + 去 ValueError → B4 测试不破。
- 回滚点：IR `initial`（R1）→ 双 V fidelity（R3）→ Lab 路由（R6）→ 前端（R7）逐段可逆。
- 测试分层：layer1 后端 pytest（test_b6_*.py：IR/双V/steps/golden via TestClient）；layer2 node/probe（前端 palette + panel）；layer3 手动 ≤5min exit 1 + 全套回归。

## 10. 验证命令

```powershell
.venv\Scripts\python.exe -m pytest -m phaseB6 -q        # B6 专项
.venv\Scripts\python.exe -m pytest -q                  # 全套（1124+ 不降）
.venv\Scripts\python -m pytest tests/test_lab_api.py::test_a8... -q  # 硬边界（bosonic 解锁 vision §6.2 同步后）
node .../probe     # 前端探针
```
