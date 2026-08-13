# Design — Fock Lab GUI（同壳双后端）

> 技术设计。边界/契约/数据流/权衡。需求见 `prd.md`。
> 术语注意：本设计「表示后端」（Gaussian/Fock representation backend）≠ `backend=` 数值后端（numpy/jax，见 spec backend-interface.md）。

## 1. 架构

```text
Browser SPA（不变的单页）
├── 顶栏: backend 切换（Gaussian/Fock）→ state.session.backend
├── 编辑器 staff 五线谱（不变）; 托盘 = OPS 按 backend 过滤
├── 结果面板:
│   ├── Gaussian: 现状 Wigner + meters + scan
│   └── Fock: 双卡（Wigner | PNR 分布柱）+ joint 2D heatmap + 采样对照 + 截断护栏
└── POST /run | /sample | /batch   body 加 "backend"

cvsim/lab/
├── ir.py       # + FOCK_WHITELIST、fock load/run/sample 路径、EXTENSION_FIELDS 扩展
├── server.py   # /run /sample 按 body["backend"] 路由; + POST /batch
└── static/     # + fock.js（Fock 面板）；ops.js/editor.js/app.js 改造
```

**单包、单进程、单端口**。`"backend"` 缺省 `gaussian` → 旧 JSON 零破坏。

## 2. 后端

### 2.1 FockCircuit 初始态 API（Q11 b，最小增量）

`cvsim/fock/circuit.py`:

- `FockCircuit(nmode, cutoff=10, initial=None)` — `initial: None | list[int]`，长度 = nmode，各分量 `0 <= n_i < cutoffs[i]`（校验失败 ValueError）。None = 全真空。
- `CompiledFock` 增加 `initial`；`_init_state()` 由真空改为 per-mode Fock 数态的 Kronecker 积（复用 `FockState.fock` 语义，m 模 = kron）。
- 密度路径（有 loss 等通道后）行为不变：初始态仍是纯态，通道转密度。

`cvsim/fock/ir.py`:

- `validate_ir` 顶层接受 `"initial"`（None 缺省 = 真空；list 校验同上）。
- `EXTENSION_FIELDS = frozenset({"view", "seed", "ui", "backend"})` 对齐高斯 ir（当前 fock validate 拒绝一切未知顶层字段，Lab JSON 带 view/seed/ui 会 422——这是本次必须修的 bug）。
- `to_ir` 输出 `"initial"` 仅当非全真空；`from_ir` 读回。

**不动** `FockState.cat`（脚本 API 保留）；**不加** cat 源节点（Kerr 协议教学路径）。

### 2.2 lab 层（cvsim/lab/ir.py）

- `FOCK_WHITELIST = frozenset({...R2 全部 op...})`，与 `LAB_WHITELIST` 并列；白名单是 UI 概念（ADR-0003 #3），core IR 全 op 集不变。
- `EXTENSION_FIELDS` 增 `"backend"`、`"initial"`（gaussian 路径忽略 `initial`）。
- `load_circuit(data)`: `data.get("backend", "gaussian")` → `"fock"` 时走 `cvsim.fock.ir.validate_ir` + 白名单校验（复用现有 `_require`/错误样式，`CircuitV0Error` → 422）；返回对象带 `backend` 标记。
- 执行路径：fock = `FockCircuit.from_ir` → `run()` / `run(rng=...)`。**零第二套物理**——测量/前馈/坍缩全走 FockCircuit 现成语义（R6 自动满足）。
- lab 层禁止 import `cvsim.fock._*`；只允许 `cvsim.fock` public（`FockCircuit`、`pnrd_probs`、`mean_photon`、`truncation_leakage` 等，全部已在 `cvsim/fock/__init__.py` 导出）。

### 2.3 端点与 payload

`POST /run`（body 含 `backend: "fock"`）返回：

```json
{
  "schema": "circuit_v1", "backend": "fock", "nmode": 2, "cutoffs": [10, 10],
  "wigner": {"x": [...], "p": [...], "W": [...]} | null,
  "dist": {"mode": 0, "probs": [0.5, 0.0, 0.5, ...]},
  "joint": {"modes": [0, 1], "grid": [[...]]} | null,
  "meters": {"mean_photon": [...], "purity": ..., "leakage": ...},
  "measured": [...]
}
```

- `dist` = 单模边缘 `pnrd_probs(state, mode=view.wigner_mode)`（截断到各模 cutoff）。
- `joint` = 2 模联合 `pnrd_probs`（仅当 `view.joint_modes` 提供且 nmode≥2 且无测量坍缩歧义；否则 null）。
- `wigner` = 复用 `wigner_grid(partial_trace(...))` 路径（Fock 版 partial_trace 已存在）；singular 条件态 → null（诚实显示）。
- `meters.leakage`：纯态用 `truncation_leakage`；密度态（通道后）→ 诚实标 null 或 trace（实现时定，原则：不造假数）。
- `POST /sample`：同 /run + `seed` + outcomes 向量；RNG = `np.random.default_rng(seed)`。
- `POST /batch`：body 含 `backend: "fock"` + `shots`（v0 UI 固定 1000；服务端校验 int 1..100000）；无测量节点时 = `pnr_sample_batch` 计数直方图（联合，维度 = cutoffs）；有测量节点时 = 按序 condition 链的 batch 采样；返回 `{"counts": [...], "shots": N, "seed": ...}`。
- `POST /scan` + `backend: "fock"` → 422（v0 无 scan，P1）。

### 2.4 性能预算

| 项 | 预算 |
|----|------|
| wigner_fock 64×64, cutoff≤20 | ≤200ms（O(N²)/点，N=cutoff） |
| cutoff>20 | UI 提示慢速；Wigner 网格自动降 N=48 |
| joint heatmap | ≤30×30=900 格，毫秒级 |
| batch 1000, cutoff≤10 | ≤1s（`pnr_sample_batch` 向量化） |

## 3. 前端

### 3.1 状态（editor.js）

- `state.backend: "gaussian" | "fock"`（缺省 gaussian，Load 时读 JSON `backend` 字段）。
- `state.initial: number[]`（fock 后端生效；toCircuitJson 时非全零才写入）。
- `state.cutoffs`（fock 后端生效；全局滑块 1..30 + per-mode 覆盖折叠区）。
- `toCircuitJson`/`stateFromJson` 双向同步含以上字段。

### 3.2 托盘（ops.js）

- `OPS` 每项加 `backends: ["gaussian","fock"]` 元数据；Fock-only：`kerr(chi)`、`cz(weight)`、`cx(weight)`、`measure_pnr(name)`；Gaussian-only：`fourier`。
- 托盘渲染按 `state.backend` 过滤；参数浮层元数据同样分表。
- Fock 后端无源节点托盘（真空起手 + 初始态卡）；`nmode` 由「加模」按钮管理。

### 3.3 新文件 fock.js（模块规则对齐 frontend/directory-structure.md）

- 分布柱状图卡（单模，SVG 柱）+ joint 2D heatmap 卡（2 模选择，格子着色）。
- 采样对照层：Measure once 结果向量 + seed 展示；Batch 按钮 → 双色叠画（理论蓝 / 采样红）。
- 截断护栏卡：cutoff 滑块 + per-mode 覆盖 + 泄漏仪表（>1% 黄）+ 慢速提示。
- outcomes 卡（测量结果向量 + seed + 条件态标记）。
- 纯逻辑（直方图构建、双色叠画数据、heatmap 网格计算）与 DOM 分开（对齐 component-guidelines）。

### 3.4 视觉

复用 Cobalt 设计系统 tokens（design-system.md）；新面板不引入新颜色语义；泄漏黄 = 现有 warning token。

## 4. 兼容与回归

| 契约 | 保证 |
|------|------|
| 旧 `circuit_v1.json`（无 backend） | 走 gaussian 路径，行为逐字节不变 |
| gaussian 路径 payload | 字段不动 |
| `cvsim.fock` 不 import `cvsim.gaussian` | ADR-0001 架构测试继续绿（lab 层不在限制内） |
| FOCK_PUBLIC 冻结表 | +`FockCircuit.initial` + IR `initial` 字段（vision-fock 文档同步） |

## 5. 权衡记录

| 决策 | 选择 | 弃 |
|------|------|----|
| 后端形态 | 单包拆层 | 独立 server 进程 / 双前端 |
| cat | Kerr 协议（displace+Kerr(π/2)） | cat 源节点（多 API、少教学） |
| 初始态 API | `initial: list[int]` 仅光子数态 | 全源工厂 API |
| joint 视图 | v0 含 2 模 heatmap | defer（丢 HOM 招牌） |
| batch | 固定 1000 | 可调 shots（P1） |
| 矩阵编辑器 | defer（白名单教义） | 托盘直给 |
