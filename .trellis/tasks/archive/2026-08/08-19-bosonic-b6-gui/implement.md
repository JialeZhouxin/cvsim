# Bosonic B6 GUI 三件套——执行计划

## 前置

- 基线：B5 commit `125aae4`，全套 1124 passed / 4 skipped。
- 激活：`task.py start 08-19-bosonic-b6-gui`（本计划 review 通过后）。

## Step 1 — `_gauss_overlap` 双 V 升级（R3）

- `cvsim/bosonic/gkp.py`：`_gauss_overlap(Va, Vb, r_i, r_j)` 通用双 V 公式；gkp 内部 Gram 调用等 V 传参。
- `cvsim/bosonic/analyse.py`：`pure_fidelity` 去等 V ValueError，`T[i,j] = _gauss_overlap(V_i^a, V_j^b, ...)`。
- ✅ 验证：B4 layer2 测试（test_b4_*.py）原样绿；新增双 V 单测（不同 V 语义 + 等 V 退化 == B4 值 atol 1e-12）。

## Step 2 — `BosonicState` 张量拼接 + `BosonicCircuit(initial)`（R1/R2）

- state.py / circuit.py：per-mode `initial` 态名解析 + 组件直积（K 乘、V 块对角、rbar 拼接、w 乘、真空补模）。
- `BosonicCircuit(nmode, initial=None)` + `from_ir` 消费 `data["initial"]` + `to_ir` 回写。
- ✅ 验证：`initial=["gkp0","gkp1"]` 构建 + run + roundtrip lossless；缺省=真空（B5 行为）。

## Step 3 — Lab 路由解锁（R6）

- `cvsim/lab/ir.py`：`BOSONIC_WHITELIST` + `_load_bosonic` + `run_bosonic_circuit`（含 `detail="steps"` 中间态摘要 + wigner）。
- `cvsim/lab/server.py`：`/run` `/sample` bosonic 分支；`/scan` bosonic→422；`/fidelity` 新端点（rounds/seed/γ sweep）。
- `cvsim/lab/__init__.py` 导出。
- ✅ 验证：TestClient `/run` bosonic golden（等价脚本 atol 1e-7）；`/fidelity` γ 曲线（γ=0→fidelity≈1, γ↑→单调降）；steps 逐段 nmode 正确；旧 Gaussian/Fock JSON 行为不变；hard-boundary test 更新（vision §6.2 bosonic 解锁）。

## Step 4 — 前端三件套（R7）

- `ops.js` backends += "bosonic"（含 cz/cx/interferometer/gaussian_channel/measure_threshold）+ initial 卡。
- `index.html`/`app.js`：backend="bosonic" 面板 = Wigner evolution view（步进滑条）+ fidelity sweep curve + step 播放。
- ✅ 验证：node/probe 探针绿；手动搭 GKP QEC 脚本 ≤5 min（exit 1）。

## Step 5 — 专项测试 + 全套回归

- `tests/test_b6_bosonic_gui.py`（`pytestmark = phaseB6`）：IR initial roundtrip、双 V fidelity 正确性、steps 段语义、Lab golden（TestClient）、旧 JSON 不变。
- `pyproject.toml`：注册 `phaseB6` marker。
- ✅ 验证：`pytest -m phaseB6` 全绿 + 全套无降。

## Step 6 — spec 同步 + vision 更新（R6 边界解锁）

- `.trellis/spec/cvsim/bosonic.md`：§6.4 B6 契约（initial 源、双 V fidelity、steps、/fidelity、Lab 解锁）。
- `docs/vision-bosonic-simulator.md`：B6 done、§6.2 bosonic Lab 解锁同步、vision v0.6.0。
- `tests/test_lab_api.py::test_a8`：bosonic 从 banned → allow（Fork 先例样式），加 `bosonic.` public import 合法化。

## Step 7 — 提交 + 归档

- commit（feat）：按段增量 2-3 个 commit（后端 / 前端）。
- OCR review 每 commit（前置 Phase 3.4）。
- `task.py finish` + `task.py archive` + `add_session.py` journal。

## 验证清单（exit 对照）

| exit | 判据 | 验证 |
|------|------|------|
| 1 | GKP QEC ≤5 min 无手写 Python | Step 4 手动 + 截图留档 |
| 2 | Bosonic JSON → /run golden（atol 1e-7） | Step 3 TestClient + 等价脚本 |
| 3 | 旧 JSON 不变 + pytest/node 绿 | Step 5 全套回归 |
| AC4 | IR initial roundtrip lossless | Step 2 单测 |
| AC5 | 双 V fidelity（等 V 退化 + γ 单调） | Step 1/3 单测 |
| AC6 | steps 段语义正确 | Step 3 单测 |

## 回滚点

- Step 1 独立可回滚（pure_fidelity 内核）；Step 2-3 依赖 Step 1。
- Step 4 前端可独立回滚（不接路由则 panel 不显）。
- 任意步失败 → 修/回退该步，重跑对应验证。
