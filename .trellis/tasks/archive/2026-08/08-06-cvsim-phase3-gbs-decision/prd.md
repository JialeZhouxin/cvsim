# GBS 路径决策 + Walrus interop

## Goal

关闭 Phase 3 退出标准 #4：GBS 路径文档化（adapter 或 explicit skip）。当前任务是 Phase 3 最后一个未完成子任务。已拍板：走 **adapter** 路线。

## Background / 已确认事实

- Vision `docs/vision-gaussian-simulator.md`:
  - L545: GBS = adapter `export_cov_for_walrus(state)` + docs；optional extra dependency
  - L546/L40: 自研 Hafnian 内核 **Avoid**（仅 phase charter 明确时才做）
  - L646: Phase 3 exit criterion 4: "GBS path documented (adapter or explicit skip)"
  - L720: The Walrus adapter 约定: export cov + μ；metadata: ħ、ordering annotation in docstring
  - L182: 架构预留 `walrus.py`（optional extras）
- cvsim 约定（`conventions.py`）: ħ=1, xxpp, vacuum V=I/2
- `cvsim/gaussian/analyse.py` fidelity 已用 thewalrus/Brask 数学转录（arXiv:2102.05748），不依赖安装 thewalrus
- thewalrus 未安装；pyproject 无该依赖；仓库无 hafnian/torontonian 自研实现
- benchmark-ci 任务 prd 将 gbs-decision 列为 follow-up

## Requirements

- **R1 路径**（拍板）: GBS 走 adapter（vision L545），不 skip
- **R2 依赖**（拍板）: thewalrus 为 optional extra（`cvsim[gbs]`）；测试 `pytest.importorskip`，未装时跳过；核心依赖不引入
- **R3 export API**: `cvsim/gaussian/walrus.py` 提供 `export_cov_for_walrus(state)`，把 cvsim (V, r̄)（ħ=1, xxpp）转成 thewalrus 约定格式（hbar=2 归一化 σ、mean），docstring 含 ħ/ordering metadata（vision L720）
- **R4 文档**: `docs/` 一段 GBS 使用说明 — 怎么构造状态、怎么导出、怎么喂 thewalrus、约定是什么、示例代码
- **R5 范围**（拍板）: 薄层三件套（walrus.py + 测试 + docs 段落），不含 GBS 教学 notebook（Phase 5）

## Acceptance Criteria

- [ ] **AC1 格式层**（无 thewalrus 也跑）: 导出函数手算可验 — 真空 → σ 归一化正确；压缩态 → 对角线符合已知公式；矩阵形状/对称性断言
- [ ] **AC2 对拍层**（`importorskip` thewalrus）: 单模压缩真空 r=1，thewalrus 计算的 P(0)/P(2)/P(4) vs 解析值 `sech(r)·(2n)!/(2ⁿn!)²·tanh²ⁿ(r)`，atol ~1e-9
- [ ] **AC3 CI**: 核心 job 不装 thewalrus（对拍测试跳过）；optional job 装 `[gbs]` 跑全量
- [ ] **AC4 文档**: `docs/` GBS 段落含约定说明（ħ、排序、metadata）+ 端到端示例代码
- [ ] **AC5 全量回归**: 既有 pytest 全绿（当前 581 个）

## Out of Scope

- 自研 Hafnian/Torontonian 内核（vision L40/L546）
- approximate GBS samplers（vision L591）
- GBS 教学 notebook（Phase 5）
- GBS 应用算法（最大团/稠密子图等）
