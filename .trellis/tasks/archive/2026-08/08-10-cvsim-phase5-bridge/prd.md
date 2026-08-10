# cvsim Phase 5 — Bridges & CV error-correction（F-BRIDGE / GKP feedforward / Bosonic consistency）

## Goal

Phase 5（vision §5）三件套：**F-BRIDGE** 观测值桥（Gauss↔Fock 小 m 矩阵元对照）、**GKP feedforward 教程**（CZ+measure+ParamRef 纠错故事）、**Bosonic consistency 测试**（三表示互证）。两前置决策已 grill 锁定（2026-08-10，vision §11 #2/#3 已 Resolved）。

## Requirements

### R1 · F-BRIDGE 观测值桥（child 1: phase5-bridge）

- 顶层模块 `cvsim/bridge.py`（ADR-0001：跨表示函数级转换，非 DSL；CVCircuit 不泛化）
- 纯函数族（grill Q2 锁定）：
  - `coherent_element(n, alpha)` — ⟨n|α⟩ 解析矩阵元
  - `squeezed_element(n, r, phi)` — ⟨n|ζ⟩ 解析矩阵元
  - `thermal_diag(n, nbar)` — 热态对角元
  - `vacuum_probability(V, rbar, mode)` — 高斯态 0 光子对角元（解析式，threshold p_click 复用）
  - `fock_state_amplitude(n, state)` — 从 FockState 取数做对照
- exit 2 主体：coherent/squeezed low cutoff 对照测试（解析 vs Fock 数值，atol 明确）
- 态桥（完整 ρ_fock 转换）不做：ponytail 标注（threshold 后验更新增强时再补）

### R2 · Threshold outcome-only（child 2: phase5-threshold）

- `cvsim/gaussian/observables.py` 加 `p_click(state, mode)` + `sample_threshold(state, mode, rng)` → bool
- 解析式：`p_click = 1 − vacuum_probability`（复用 bridge 数学，私有 helper 不双开 API）
- **outcome-only**：无态更新（grill 2026-08-10）；docstring 明确标注
- `GaussianCircuit.measure_threshold(mode, name)` builder + 编译链路（outcome 可作为 ParamRef 源，为 R3 铺路）
- 不强制转 Fock；不接受非高斯输入（GaussianState 输入校验）

### R3 · GKP feedforward 教程（child 3: phase5-gkp-tutorial）

- `tutorials/06_gkp_feedforward.ipynb`（中文教学，_build_06.py 构建，风格同 05）
- 故事：**GKP 逻辑比特 + 位移错误检测**（grill Q4 锁定）—— GKP 态（强挤压 Gaussian 近似，诚实标注非理想峰）→ CZ 纠缠 data+ancilla → homodyne 测 ancilla → 读出位移误差 → ParamRef 反馈修正
- exit 1 主体：CZ + measure + ParamRef 三要素齐全，电路经 `compile().run(values)` 全链路
- 教程含自检断言（Run-All 可执行）；Gaussian 近似局限性写入 markdown

### R4 · Bosonic consistency（child 4: phase5-bosonic-consistency）

- 把 spec 已写 Bosonic 合同（vacuum 单分量、加权矩、loss w 不变、单分量==Gaussian）从文档变测试
- **桥锚定**（grill Q5 锁定）：cat/GKP 多峰态的 ⟨x⟩/Var 与解析/Fock 对照（复用 bridge 数学）
- 纠缠量跨表示（log-neg 截断收敛）不做：ponytail

## Out of Scope

- 完整态桥（Gaussian → ρ_fock 通用转换）
- CVCircuit 泛化 / DSL 化 bridge
- threshold 点击后的高斯态更新
- GKP 理想峰（完美 GKP 态制备）
- PNR 测量（vision 已列，非本 Phase 交付）

## Acceptance Criteria

- [ ] AC1（exit 2）bridge 测试：coherent/squeezed 低截断矩阵元解析 vs Fock 数值一致（atol ≤ 1e-10 量级，截断内）
- [ ] AC2（exit 1）GKP 教程：CZ + measure + ParamRef 电路文档化 + Run-All 通过 + 检测→修正闭环断言
- [ ] AC3 threshold：`p_click` 与 Fock 截断对角元数值一致（真空/相干/挤压态测试）；outcome 采样分布正确；circuit builder + ParamRef 链路可编译运行
- [ ] AC4 bosonic：现有合同测试化 + cat/GKP 矩桥锚定测试
- [ ] AC5 全量 pytest 保持绿（Phase 4 基线 700）；每 child commit + OCR review（服务端不稳时 trellis-check 兜底）
- [ ] AC6 收口：vision v0.4.0（Phase 5 close + gap table）、CONTEXT.md 术语、spec 更新、parent 归档

## Notes

- 前置决策：grill 2026-08-10（Q1 观测值桥 / Q2 函数族 / Q3 observables 解析式 / Q4 GKP 纠错故事 / Q5 桥锚定 / Q6 4 切）
- child 顺序：bridge → threshold → gkp-tutorial → bosonic-consistency（④ 不依赖 ②③ 但串行跑，单一 writer）
- 基线：700 passed / 6 skipped（Phase 4 后）
