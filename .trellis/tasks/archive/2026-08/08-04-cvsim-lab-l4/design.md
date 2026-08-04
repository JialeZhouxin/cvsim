# Gaussian Lab L4 — Design

## 1. 架构边界

```
┌─ Browser SPA ─────────────────────────────┐
│ 扫参面板: node select + param select      │
│ + min/max/n + modes_A 下拉 + SVG 曲线      │
│ (ops.js 新增 amp/mz 托盘卡片)              │
└───────────────┬───────────────────────────┘
                │ POST /scan            POST /run
┌───────────────▼───────────────────────────┐
│ server.py: /scan 端点 (validate → scan)   │
│ ir.py: scan_circuit() + mz/amp 组合       │
│         → cvsim.gaussian 公共 API 循环     │
└───────────────────────────────────────────┘
```

## 2. 数据流与契约

### 2.1 `POST /scan`（server.py）

请求（circuit_v0 + sweep 段）：
```json
{
  "schema": "circuit_v0", "seed": 0,
  "nodes": [...], "edges": [], "view": {...}, "ui": {},
  "sweep": {"node_id": "s0", "param": "r", "min": 0.0, "max": 2.0, "n": 50, "modes_A": [0]}
}
```

校验（422 语义，沿用 `CircuitV0Error` → `{detail}`）：
- node_id 存在且 op 的参数含 `param`；param 值为实数数值（复数 alpha 拒绝）
- min/max 有限数且 min < max；n 整数 ∈ [2, 200]
- modes_A：非空 int 列表，∈ [0, nmode)，长度 ≤ nmode-1
- 测量节点（homodyne/heterodyne）出现在被扫电路 → 422？**决策**：扫描电路含测量节点 → 拒绝（E_N 定义于高斯态，条件态 singular 无 E_N；诚实拒绝）

响应：
```json
{"node_id": "s0", "param": "r", "min": 0.0, "max": 2.0, "n": 50,
 "modes_A": [0], "xs": [0.0, ...], "ys": [0.0, ...]}
```
- 纯函数：无 RNG，同请求必同响应
- 每点：`run_circuit(copy(circuit, param=v))` → `meters.log_negativity`；singular（无定义）→ ys 置 null（曲线断点，前端跳过）
- 线性取点 `xs = linspace(min, max, n)`

### 2.2 MZ 组合（ir.py `_apply`）

```python
if op == "mz":
    theta = _num(p.get("theta"), where, "theta")
    phi = _num(p.get("phi", 0.0), where, "phi")
    st = beamsplitter(state, modes[0], modes[1], theta, 0.0)
    st = phase(st, phi, modes[0])
    return beamsplitter(st, modes[0], modes[1], theta, 0.0), None
```
- 双模 op：TWO_MODE_OPS 加 `"mz"`；`modes` 必填、2 元素、越界 422
- 等值测试：`mz(theta, phi)` ≡ `bs(theta,0) → phase(phi,m0) → bs(theta,0)`（RunResult meters + V 全等，atol 1e-12）

### 2.3 amplifier（ir.py `_apply`）

```python
if op == "amplifier":
    G = _num(p.get("G"), where, "G")
    nbar = _num(p.get("nbar", 0.0), where, "nbar")
    return amplifier(state, G, mode, nbar), None
```
- 单模 op：SINGLE_MODE_OPS 加 `"amplifier"`；G<1 / nbar<0 → 422（后端 ValueError 转 CircuitV0Error）
- advanced 参数策略沿用 L2：`nbar` 缺省填 0，不冻结

### 2.4 ops.js 元数据

```js
amplifier: { label: "放大", kind: "single", params: { G: {min:1, max:8, step:0.05, sweep:[1,4]}, nbar: {advanced:true, sweep:false} } },
mz: { label: "马赫-曾德尔", kind: "two", params: { theta: {sweep:[0, Math.PI]}, phi: {sweep:[0, Math.PI]} } }
```
- 新增 `sweep: [min, max]` 元数据 = 可扫参数 + 自适应默认范围；无 sweep 字段 = 不可扫（alpha 等）
- 现有 op 补 sweep 元数据：tmsv.r [0,2]、squeeze.r [0,2]、loss.T [0,1]、beamsplitter.theta [0,π]、two_mode_squeeze.r [0,2]、phase.phi [0,π]…（conservative 默认，可改）

## 3. 前端扫参面板（app.js + style.css）

- 面板位置：右侧 meters 下方（Wigner 之下、measurement-panel 之上）
- 控件：`node select`（现有节点，op 有可扫参数才列出）→ `param select`（该节点可扫参数）→ `min` / `max` / `n` 输入（自适应默认）→ `modes_A` select（1..nmode-1 规模，默认 [0]，2 模电路自动 [0]）→ `Scan` 按钮
- 曲线：`<svg>` 折线 + 轴 + 网格（自研，零依赖；参考 Wigner canvas 的 token 配色）；断点（null ys）跳过
- 状态：扫描中按钮 busy；失败 status 红条
- 不写回 circuit_v0：sweep 配置仅前端 state

## 4. 兼容性与回归

- `/run`、`/sample`、Save/Load 完全不动（sweep 段只在 /scan 请求体，不进 circuit_v0 schema）
- 白名单扩增影响：load_circuit 校验天然兼容（WHITELIST 加成员）；editor.js 的 OPS 查找走 `Object.hasOwn` 自动获得新 op
- 测试：`tests/test_lab_l4.py`（scan 端点 + mz/amp 等值 + 校验矩阵）、`tests/editor.test.mjs` 加 ops 元数据断言（可选）、headless CDP 探针（面板渲染 + 曲线点）

## 5. 风险与回滚

- MZ 组合顺序错误 → 等值测试兜底（atol 1e-12 与显式序列对照）
- /scan 性能：n=200 × 电路重建最坏 ~1s（m≤6 实测毫秒级/点）；超限 n>200 拒绝
- 回滚：单一 commit 可 revert；白名单 amend 与代码同 commit（vision 文档一起回滚）
