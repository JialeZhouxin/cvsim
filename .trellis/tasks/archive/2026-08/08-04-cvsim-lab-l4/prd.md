# Gaussian Lab L4 — E_N(r) 扫参 + 白名单扩增（amp / MZ）

## Goal

Lab L4 / P1（vision-gaussian-lab-ui.md §10）：**单参数扫描 → E_N 曲线**（F-LAB-SCAN）+ **amplifier / MZ 进白名单**。undo 已拆出（独立任务，不在本任务）。

## Background

- 后端已有：`amplifier(state, G, mode=None, nbar=0)`（channels.py L147）、`beamsplitter`/`phase`（gates.py）、`log_negativity(state, modes_A=[...])`（F-ANALYSE-3）
- Lab 白名单现状（ir.py L38-43）：9 ops；amp/MZ 缺
- 规则：加托盘 op 先 amend vision §4（§13.2）；lab 层组合调 gaussian 公共 API 合法（§6.2 API boundary）

## Requirements

### R1 — amplifier 进白名单
- 单模 op `amplifier`；主参数 `G`（≥1）；`nbar`（≥0，**advanced**，缺省填 0 = 量子极限，与 loss 同模式）
- 三处同步：vision §4 → ir.py WHITELIST/SINGLE_MODE_OPS → ops.js 托盘

### R2 — MZ 进白名单
- 双模 op `mz`；参数 `theta`（分束角）+ `phi`（相位差）；**lab 层组合**实现：`BS(θ) → phase(φ, m0) → BS(θ)`（调 gaussian 公共 API，不加后端门）
- 三处同步同上

### R3 — 单参数扫描 → E_N 曲线（F-LAB-SCAN）
- 后端 `POST /scan`：body = circuit_v0 + `{node_id, param, min, max, n, modes_A}`；响应 `{xs, ys, param, node_id, modes_A}`（ys = 各点 log_negativity；**纯函数无 RNG**）
- 可扫参数：**实数数值参数**（r / T / G / theta / phi 等）；复数参数（alpha）不可扫（前端过滤）
- 前端扫参面板：节点 select + 参数 select + min/max/n 输入 + modes_A 下拉（1..nmode-1，默认 [0]）+ SVG 折线（零依赖）
- 自适应默认范围：r: 0–2、G: 1–4、T: 0–1、theta/phi: 0–π；n=50
- **扫参配置不写回** circuit_v0 JSON（UI 会话态；schema 稳定）

## Acceptance Criteria

- [ ] **A7 扫参**：TMSV r 扫参曲线 E_N(r) 与解析 `2r/ln2` 一致（atol 1e-6，n≥20 点全对）；/scan 端点 pytest 覆盖（含非法参数 4xx：越界 mode、非数值 param、min>max、n 越界）
- [ ] **A8 amp**：拖拽 amplifier 可用；/run 单点与后端 `amplifier()` 对照；G<1 → 422；nbar advanced 缺省 = 0
- [ ] **A9 MZ**：拖拽 mz 可用；/run 结果与"BS+phase+BS"等效电路一致（后端组合对照测试）；theta/phi 范围校验
- [ ] **A10 面板**：headless CDP 验证扫参面板渲染曲线、modes_A 下拉在 2 模电路正确默认、>2 模可用
- [ ] **A11 回归**：pytest 全绿（430+新增）、node --test 全绿、ruff lab 干净、vision §4 白名单已 amend + changelog

## Out of Scope

- undo（独立任务）
- 通用多参数/多 meter 扫描（本任务只扫 E_N 单曲线）
- 扫参配置持久化
- 后端新增物理门（MZ 用组合）
- 模拟器 Phase 3（compile/batch）

## Technical Notes

- /scan 每个点重建电路（无 compile 缓存；m≤6、n=50 毫秒级，可接受）
- modes_A 语义沿用 log_negativity 现有参数（A 组 mode 索引列表）
- ops.js 参数元数据需标记"可扫"（实数数值）；displace 的 alpha 排除
- vision §4 白名单 amend 是 R1/R2 前置（规则 §13.2）
