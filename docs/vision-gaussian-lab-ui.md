# Vision: Gaussian Lab UI (local interactive workbench)

> **Audience:** AI coding agents and human maintainers.  
> **Role:** Product SoT for the **graphical Gaussian lab** front-end.  
> **Physics / API SoT remains:** [`vision-gaussian-simulator.md`](./vision-gaussian-simulator.md) + [`api-stability.md`](./api-stability.md).  
> **This doc wins** for UI scope, interaction, and v0 acceptance. If it conflicts with simulator vision on **math/conventions**, simulator vision wins and this doc must be amended.

**Last updated:** 2026-08-05  
**Status:** Locked direction after grilling (user chose “按推荐走”); L0–L4 landed (L4 = F-LAB-SCAN + amp/MZ whitelist, undo separate task)
**Codebase today:** Lab UI package landed through L4; backend calls public `cvsim.gaussian` + `cvsim.wigner` only.

---

## 1. One-liner

> **本机单页光路板**：用拖拽搭 **高斯** 电路（对齐 `GaussianCircuit`），默认在右侧看 **选定单模的 Wigner 热图**；需要时拧参数、读分析量、点一次测量抽样。不为教学平台、不为多用户、不为真机。

**Primary user (v0):** 作者本人（研究/调参加速）— 唯一用户假设。  
**Shell:** 本地 Web（浏览器 UI + 本机 Python 薄后端）。  
**Soul experience (P0):** 单模 Wigner 热图随电路/参数防抖刷新。  
**Secondary (P0.5 / P1):** 分析量仪表、`E_N(r)` 等扫参曲线。

---

## 2. Purpose & non-goals

### 2.1 Purpose

| Goal | Meaning |
|------|---------|
| Faster than scripts | 搭常见高斯光路、看态、拧参，不必每次写 Python |
| Trust the picture | Wigner + meters 必须与 `cvsim` 数值一致（同一套约定） |
| Path to serialize | 电路 JSON 从 v0 起就是 Phase 3 serialize 的草案（`circuit_v0`） |
| Lab feel | 可选 **Measure once**（真抽样），默认仍是可复现的解析仪表 |

### 2.2 Non-goals (explicit forever-until-phase)

下列 **v0 与近端明确不做**（grilling 已砍；未经修订本文不得开做）：

| 砍项 | 说明 |
|------|------|
| 多用户账号 / 权限 | 单机单用户 |
| 云端算力 | 计算只在本机 |
| Fock / Bosonic UI | 高斯专用；路由层不留「以后接 Fock」的半吊子 hook |
| 真机硬件控制 | 无 device backend |
| 3D 光路 / 光学桌隐喻 | 2D 节点图即可 |
| 协作编辑 | — |
| 论文级一键美化导出 | 可截图；不做排版产品 |
| AD / 优化闭环 | Phase 4 模拟器能力，不进 Lab v0 |
| 手机端布局 | 桌面浏览器宽度 |
| i18n 框架 | UI 文案先中文（或中英混排固定字符串），不做语言包 |
| 双模联合 Wigner | v0 仅单模 + `partial_trace` |
| 通用 `(X,Y)` 通道矩阵编辑器 | — |
| Streamlit/Gradio 作为主壳 | 拖拽电路会被迫重写 |
| 完整 `GaussianCircuit` op 1:1 托盘 | **白名单制**（§4） |

### 2.3 Relationship to simulator phases

| Simulator | Lab UI |
|-----------|--------|
| Phase 1–2 Gaussian core + analyse + measure | **Prerequisite**（已完成） |
| Phase 3 serialize / compile / batch sample | Lab `circuit_v0` JSON **提前探路** serialize；compile 优化可后接 |
| Phase 4 AD | Out of Lab scope until explicit unlock |
| Teaching notebooks | 并行；Lab **不是** notebook 替代品，是工作台 |

Simulator vision §1.3 historically listed “GUI circuit editor = out of scope”. **This document is the explicit UX-phase unlock** for a **local Gaussian-only** lab. It does **not** unlock cloud, multi-user, or multi-representation GUI.

---

## 3. Product stance

1. **UI 不实现物理** — 禁止在前端或后端手写第二套辛矩阵 / Wigner 公式；一律调用公开 `cvsim` API。  
2. **硬约定不漂移** — \(\hbar=1\)，xxpp，\(V_{\mathrm{vac}}=I/2\)，位移 \(\sqrt{2}\) 规则；见 simulator §2 与 `api-stability.md`。  
3. **白名单 > 通用 IDE** — v0 托盘是刻意偏瘦的子集；「能拖模拟器里所有门」是 P2+ 幻想，不是 v0。  
4. **Wigner 是主循环** — 布局与性能预算优先保证单模热图；扫参曲线不得反客为主。  
5. **默认可复现** — 解析 meters 默认路径；抽样必须显式按钮，并显示 seed。  
6. **丑但快可接受** — 唯一用户；先通主剧本，再美化。

---

## 4. v0 component whitelist

Exceeding these counts requires amending this doc first.

### 4.1 State factories（画布源节点 ≤3）

| ✅ v0 | ❌ defer |
|-------|----------|
| `vacuum` | `thermal` as source |
| `coherent` | `displaced_squeezed` |
| `tmsv`（**L5: JSON-only**，出托盘 `palette:false`，后端/IR 保留兼容；纠缠由 `two_mode_squeeze` 门构建） | explicit `product` node（多源 + 线拼接） |

### 4.2 Gates（≤7）

| ✅ v0 | ❌ defer |
|-------|----------|
| `displace` | `cz` / `cx` |
| `phase` | `interferometer` / mesh / 任意 U |
| `squeeze` | |
| `fourier` | |
| `beamsplitter` | |
| `two_mode_squeeze` | |
| `mz`（马赫-曾德尔：`BS(θ)→phase(φ,m0)→BS(θ)` 组合，lab 层不新增门） | |

### 4.3 Channels（≤2）

| ✅ v0 | P0.5 | ❌ defer |
|-------|------|----------|
| `loss` | — | `phase_noise`, generic `(X,Y)` |
| `amplifier`（`G` 主参，`nbar` advanced 缺省 0 = 量子极限） | | |

### 4.4 Measurements（≤2）

| ✅ v0 | Notes |
|-------|--------|
| `homodyne` | 与 `GaussianCircuit` / `homodyne_condition` 语义对齐；测后是否删模跟模拟器电路一致 |
| `heterodyne` | condition **移除**被测模（api-stability §5） |

### 4.5 Result-pane widgets

| Priority | Widget |
|----------|--------|
| **P0 soul** | 单模 **Wigner** 热图 + `mode=k` 选择器；内部 `partial_trace` |
| **P0** | 态摘要：`nmode`、physical 标志（可选 `is_physical`） |
| **P0.5** | meters：`mean_photon`、`purity`、`log_negativity`（`modes_A` 选择） |
| **P0.5** | **Measure once**（`homodyne_sample` / `heterodyne_sample` + condition 路径） |
| **P1** | 参数扫描曲线（如 \(E_N(r)\)，**landed L4**）；撤销栈；多文档 |
| **L5** | **五线谱式电路编辑器**（landed）：每模一轨道、拖放放置、双模两步选择、水平 x=时序、参数浮层 |

### 4.6 Wigner policy

| Rule | Value |
|------|--------|
| Support | **Single-mode only** in v0 |
| Multi-mode | User selects view mode `k`; backend `partial_trace(state, keep=[k])` then `wigner_grid` |
| Default grid | `lim=±5`, `N=64`（先快后靓） |
| Debounce | 100–150 ms on param drag |
| Latency target | ≤200 ms typical；>500 ms must show loading |
| Degrade | optional drop to `N=48` before spinner-only |
| Joint 2-mode Wigner | **Out** of v0 |

---

## 5. Acceptance script（v0 Done 的唯一主剧本）

无手写 Python，冷启动后 **≤5 分钟** 完成：

1. 空白画布 → 拖 **TMSV**（设 \(r\)）。  
2. 两臂各拖 **loss**（设 \(T\)）。  
3. 选择 mode 0/1 → 右侧 **Wigner** 呈热态圆斑；增大 \(r\) 斑变胖（防抖刷新）。  
4. 两模间拖 **beamsplitter** → 再读 Wigner / `log_negativity`。  
5. 拧 \(r,T\) → Wigner 与 meters 刷新；`log_negativity` 在 \(T=1\)、无额外混态时应贴近 TMSV freeze \(-\log_2(e^{-2r})\)（数值 tol）。  
6. 拖 **heterodyne** on mode 0 → 电路运行后态 **少一模**；剩余模 Wigner 接近纯态相干峰（导引）。  
7. 可选：点 **Measure once**，看到一次结果与 seed。  
8. **Save JSON → 刷新页面 → Load** → 拓扑与读数一致。

做不到 1–6+8 = v0 未完成。  
主剧本不需要的托盘项（CZ、interferometer…）**不得**为了「完整」塞进 v0。

---

## 6. Architecture

### 6.1 Slice (v0 = 12b + thin API backend)

```text
┌─────────────────────────────────────────────────────────┐
│  Browser SPA (desktop width)                            │
│  Left: circuit graph editor (whitelist nodes)           │
│  Right: Wigner heatmap + thin meter bar + Measure once  │
│  Top/modal: Save / Load circuit_v0 JSON                 │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP POST /run  (and /sample if split)
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Local Python backend (FastAPI or Starlette)            │
│  • validate circuit_v0 JSON                             │
│  • build GaussianState + apply gates/channels/measures  │
│    via public cvsim.gaussian only                       │
│  • wigner_grid(partial_trace(...), lim, n)              │
│  • meters: purity, log_negativity, mean_photon, ...     │
│  • optional sample_once(seed)                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
               cvsim (numpy)
```

| Choice | Lock |
|--------|------|
| Shell | **Local Web** — not pure Qt as primary; not cloud |
| Backend | **Thin FastAPI/Starlette** — not Streamlit main shell |
| Frontend | SPA + graph lib（React Flow / LogicFlow / 等价）或极简自研节点；框架在 implement 阶段选定，**不在此锁定商标** |
| Run model | Param change → debounced **full circuit re-run**（v0 无增量缓存义务） |
| Multi-doc / undo | Out of v0 |
| Scan panel \(E_N(r)\) | **P1**，不定义 v0 切片 |

### 6.2 API boundary (hard)

**Allowed imports in Lab backend**

- `cvsim.gaussian` public `__all__`
- `cvsim.wigner.wigner_grid`（及文档化的公开 wigner 辅助）
- `cvsim.conventions` 只读常量（若需要展示）

**Forbidden**

- `cvsim.gaussian._*` / 任何 private
- 在 Lab 内复制 `analyse` / symplectic 公式「图个方便」
- 调用 Fock/Bosonic 包（v0）

### 6.3 Randomness

| Path | Behavior |
|------|----------|
| Default meters + Wigner | 纯函数；无 RNG |
| Measure once | 使用显式 `seed`（UI 显示；可改）；后端 `np.random.default_rng(seed)` |
| Reproducibility mode | 默认 on：同一 circuit + seed → 同一 shot |

---

## 7. `circuit_v0` JSON（serialize 探路）

规范性 schema 在实现任务中冻结并附 golden file；此处定 **设计约束**：

1. 版本字段：`"schema": "circuit_v0"`.  
2. 节点：`id`, `op`（白名单枚举）, `params`, 可选 `modes` / `mode`.  
3. 边：明确模线连接（或有序 ports）；**禁止**含糊的「隐式全局模号」而不写进 JSON。  
4. 与 `GaussianCircuit` 的映射必须 **可测试**：JSON → run → 与手写等价 Python 电路 state 的 `V,rbar` 一致（atol 约定）。  
5. 不得出现 UI 专用物理字段（如像素坐标可放 `ui` 子树，后端 `/run` **忽略** `ui`）。  
6. Phase 3 正式 serialize 可演进 schema；破坏性变更走版本号 `circuit_v1`，不静默改语义。

**Sketch（非最终 schema）**

```json
{
  "schema": "circuit_v0",
  "seed": 0,
  "nodes": [
    {"id": "s0", "op": "tmsv", "params": {"r": 0.6}, "modes": [0, 1]},
    {"id": "l0", "op": "loss", "params": {"T": 0.8, "nbar": 0.0}, "mode": 0},
    {"id": "l1", "op": "loss", "params": {"T": 0.8, "nbar": 0.0}, "mode": 1},
    {"id": "bs", "op": "beamsplitter", "params": {"theta": 0.785398163}, "modes": [0, 1]},
    {"id": "m0", "op": "heterodyne", "params": {}, "mode": 0}
  ],
  "edges": [],
  "view": {"wigner_mode": 0, "lim": 5.0, "n": 64},
  "ui": {}
}
```

实现时可改为纯 `GaussianCircuit` 指令列表；**以等价性测试为准**，不以此 sketch 绑架。

---

## 8. Backend endpoints（最小）

| Endpoint | Role |
|----------|------|
| `POST /run` | Body: `circuit_v0` (+ view). Returns: `nmode`, `rbar`, `V`（或摘要）, `wigner: {x,p,W}`, `meters`, `measured` 元数据 |
| `POST /sample`（可与 `/run` 合并） | Measure once；要 `seed` |
| `GET /health` | 版本 / cvsim 可 import |

v0 不要求 WebSocket；防抖在前端做完再 POST。

---

## 9. Performance budget

| Action | Target |
|--------|--------|
| Full run + Wigner \(N=64\), \(m\le 4\) | ≤200 ms local typical |
| Drag debounce | 100–150 ms |
| Slow path | loading indicator if >500 ms |
| Mode count v0 comfort | \(m \le 6\) 够用；不承诺 \(m\sim 100\)（那是模拟器 Phase 3） |

---

## 10. v0 acceptance checklist（残忍表）

发布「Lab UI v0」前作者自检：

- [ ] **A1** 冷启动 &lt; 30s 到可编辑画布（本机已装依赖前提下）  
- [ ] **A2** 无手写 Python 完成 §5 主剧本  
- [ ] **A3** \(T=1\) TMSV：`log_negativity` 与 \(-\log_2(e^{-2r})\) 在 tol 内  
- [ ] **A4** Wigner(vacuum) 中心峰值与 `wigner_grid` 直调一致  
- [ ] **A5** Save → reload → 拓扑与 meters 一致  
- [ ] **A6** Measure once：显示 seed；同 seed 可复现  
- [ ] **A7** 仍无：账号、云、Fock、3D、多参数扫参工作室、手机布局、非白名单 op  
- [ ] **A8** 后端 grep：无 `cvsim.gaussian._` private import  
- [ ] **A9** 至少 1 个 golden：JSON fixture → `V,rbar` vs 脚本电路  

---

## 11. Phased delivery（Lab 自身，不是模拟器 Phase）

| Lab slice | Deliverable | Exit |
|-----------|-------------|------|
| **L0** | `circuit_v0` 草案 + `POST /run` 无拖拽（固定 JSON → Wigner JSON） | A4、A9 雏形 |
| **L1** | 结果只读页 + 参数 query/JSON 编辑 | 主剧本无 BS 版可看热图 |
| **L2** | 拖拽编辑器 + 白名单 + 主剧本全通 | A2、A3 |
| **L3** | Save/Load + Measure once | A5、A6 |
| **L4 / P1** | \(E_N(r)\) 扫参（F-LAB-SCAN）、amp、MZ（undo 独立任务） | A7–A11 |

**Recommended implement order:** L0 → L2 可部分并行（IR 先于皮），但 **不可** 先做漂亮壳后接物理。

---

## 12. Feature IDs（for agents）

| ID | Name | Slice |
|----|------|-------|
| **F-LAB-IR** | `circuit_v0` schema + golden equivalence tests | L0 |
| **F-LAB-API** | Local FastAPI `/run` (+ `/sample`) | L0–L1 |
| **F-LAB-WIGNER** | View-mode ptrace + `wigner_grid` payload | L0 |
| **F-LAB-METERS** | purity / nbar / log_neg panel | L1–L2 |
| **F-LAB-EDITOR** | Whitelist graph editor | L2 |
| **F-LAB-IO** | Save/Load JSON | L3 |
| **F-LAB-SHOT** | Measure once + seed | L3 |
| **F-LAB-SCAN** | Param sweep curves — \(E_N(r)\) 单曲线（P1） | L4（landed） |

每个实现任务必须映射到上表；超白名单 = 先 amend 本文。

---

## 13. Agent rules（Lab）

1. 改物理语义 → 先改 **simulator vision** / `api-stability`，再改 Lab。  
2. 加托盘 op → 先改 **本文 §4**，再写 UI。  
3. 禁止为 demo 硬编码假 Wigner。  
4. 教程 notebook 与 Lab 并行；不要把 notebook 当 Lab 后端。  
5. 与 Phase 3 serialize 冲突时：更新 schema 版本 + 测试，不静默转译。

---

## 14. Changelog

| Ver | Date | Note |
|-----|------|------|
| 0.1.0 | 2026-07-30 | Initial lock from grill-me: user A/电路图/Wigner 灵魂/本地 Web/双轨测量；adopt recommended whitelist & 12b slice |
| 0.2.0 | 2026-08-03 | **L0 landed**: `cvsim.lab` — `circuit_v0` IR (validation + compile-and-run, ordered-node semantics, runtime mode remap after heterodyne), FastAPI `/run` + `/health`, Wigner+ptrace payload, meters; golden equivalence + A4/A8/A9 guards (24 tests); lab extra in pyproject. No frontend / `/sample` (L1–L3). |
| 0.3.0 | 2026-08-03 | **L1 landed**: static workbench page (JSON edit → `/run` → canvas Wigner heatmap + meters + r̄/V tables), FastAPI `StaticFiles` mount + `python -m cvsim.lab` entry; Hallmark design pass (genre=modern-minimal · theme=Cobalt · macrostructure=Workbench, offline system-font substitution); zero external deps/CDN (offline guard test); 5 UI tests (suite 409). No drag editor (L2) / save-load-sampling (L3). |
| 0.4.0 | 2026-08-03 | **L2 landed**: sequence editor — palette DnD (8 ops: tmsv/coherent/squeeze/phase/displace/loss/beamsplitter/heterodyne) appends nodes, per-node param sliders (debounce 120ms + seq guard), ↑/↓/delete, JSON⇄graph two-way sync (400ms rebuild, frozen-graph on invalid), wigner_mode selector; A3 T=1 TMSV log_neg = -log₂(e⁻²ʳ) verified; 10 node tests + suite 412. No canvas/edges (ordered-node semantics kept), no modes_A selector (2-mode unique bipartition; add with 3-mode circuits), no undo (P1) / save-load-sampling (L3). |
| 0.5.0 | 2026-08-04 | **L3 landed**: Save/Load (A5) + Measure once (A6) — `POST /sample` with explicit `seed` (`np.random.default_rng`), true sampling of all measurement nodes in node order with conditioning chain (homodyne `homodyne_sample_and_condition` keeps mode, heterodyne removes mode), homodyne op + `phi` param (default 0) in IR/ops/palette; browser Save (download `circuit_v0.json`, seed only, no outcomes) / Load (FileReader → double validation → rebuild → auto `/run`, invalid keeps current circuit); conditional-state view (outcomes + seed + singular marker; homodyne singular view → `wigner: null` + meters.singular, no fabricated data; purity/log_neg → None, mean_photon honest); `/run` stays pure (no RNG, L2-identical); 12 backend L3 tests + 4 API + 5 node + 2 UI (suite 429, node 17). No seed write-back to JSON, no localStorage, no undo / batch sampling / sweep (L4). |
| 0.6.0 | 2026-08-04 | **L4 landed**: F-LAB-SCAN `POST /scan` — sweep `{node_id, param, min, max, n, modes_A}` over real-numeric params only (`alpha`/`nmode` excluded; per-op sweepable set mirrors ops.js `sweep` metadata), measurement-node circuits rejected 422 (E_N undefined on conditional states), per-point `log_negativity(state, modes_A)` (singular → `null`), pure no-RNG, `n ∈ [2,200]`, linear `xs`; whitelist §4 amended + ir.py WHITELIST + ops.js palette: `amplifier` (`G` main, `nbar` advanced default 0 = quantum-limited, G<1/nbar<0 → 422 via library guard) and `mz` (`BS(θ)→phase(φ,m0)→BS(θ)` lab composition, two-mode op, unitary → E_N preserved, equivalence tests atol 1e-12); scan panel (node/param selects + min/max/n + modes_A 1..nmode-1 default [0] + zero-dep SVG polyline with null breaks; sweep config is UI-session state, never written back to circuit_v0). Suite 469, node 20. No undo (separate task), no multi-param scan, no scan persistence, no new backend gates. |
| 0.7.0 | 2026-08-05 | **L5 landed**: staff 五线谱编辑器（替换列表式前端；`circuit_v0` IR + 后端零改动）。每模一横向轨道（行序 = mode 升序），水平 x = 时序；执行序 = 数组序 = 按 **(x, 模序号)** 稳定排序（双模取 `modes[0]`；源恒前）；单模门拖到轨道落定 `mode`；双模门（BS/MZ/双模压缩）两步放置——拖到轨道 A → 半透明预览 + 高亮 + 状态提示 → 点击轨道 B 落定，Esc/空白取消、同模拒绝；`ui.x` 持久化于节点 `ui` 字段（旧 JSON 无 `ui.x` 按数组序排格子，源无布局）；源重构：palette = `vacuum`(+1 模，`nmode` advanced JSON-only) + `coherent`，`tmsv` 出托盘（JSON-only 兼容，旧文件可载入运行），删源连带删除作用其模上的门（先确认）；参数编辑 = 点击门/源弹浮层卡（滑块+数字，实时 JSON 同步 + 就地重跑）；门拖动改 x 重排、悬停 × 删除；可扫门浮层自动同步 scan 目标；JSON 文本域收为折叠区（双向同步 + frozen-graph 保留）；托盘图标化两列紧凑。Suite 470, node 28, staff probe 16/16 headless CDP。No undo, no parallel columns（IR 线性顺序语义保留）, no 双模门拖放改 modes。 |
