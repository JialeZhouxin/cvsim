# PRD — Phase F5: Fock bridges + integration

## Goal

Vision §4 F5（`docs/vision-fock-simulator.md` F5 节）：observation bridge 提升为正式双向 API + 可观测传播
+ threshold/PNR 交叉核对 + 双表示同一实验教程。

## Vision 原文要求（F5 退出判据）

1. Bridge cross-check suite: Gaussian analytic vs Fock numeric agree atol 1e-7 (small m).
2. Threshold (p_click) and PNR expectations agree where both apply.
3. Tutorial: same physical experiment simulated in both representations, results reconciled.

## Background（已确认事实，2026-08-12）

- **Gaussian 侧 F-BRIDGE 已完成**（vision-gaussian §5）：`cvsim/bridge.py`（顶层，105 行）+ `tests/test_bridge.py` 25 测试（atol 1e-9..1e-7）。
- `bridge.py` 现有：`coherent_element`/`squeezed_element`/`thermal_diag`（解析 Fock 矩阵元）+ `vacuum_probability(V, rbar, mode)`（Gaussian 解析 P(0)，多模约化）+ `fock_state_amplitude`。
- Gaussian threshold 桥已落地：`p_click`（实现 = 1 − `bridge.vacuum_probability`，outcome-only）/`sample_threshold`/`measure_threshold` + IR round-trip；Gaussian loss 通道存在（`gaussian.channels.loss(T)`）。
- Fock 侧可观测齐全：`mean_photon`/`pnrd_probs`（单模 + marginal）/`pnr_sample_batch`；loss Kraus（F1）；`FockState.coherent/squeezed` + `FockDensity.thermal`。
- **Q1 已由证据决定（2026-08-12 实测）**：Fock `pnrd_probs` vs bridge 元素平方 — coherent/thermal 机器精度（2.8e-16），squeezed 3.4e-8（cutoff=20，r=0.5，纯截断泄漏驱动）。→ **零新公开 API**，cross-check 用现有面；"Fock→Gauss 容差内否则 reject" = 测试/教程纪律 + 泄漏标注（test_bridge.py 既有风格）。
- **Q2 已拍板（用户）**：教程 = 有损相干态 η 扫掠（选项 A）— Gaussian 解析（⟨n⟩=η|α|²，p_click=1−e^{−η|α|²}）vs Fock 截断（loss Kraus + pnrd_probs）；覆盖全部 3 条退出判据 + 截断工程叙事。
- FOCK_PUBLIC 冻结：bridge 顶层模块、fock 包零改动 → 冻结零影响。
- 全套件 923 passed（F4 关闭）。

## Requirements

- R1: 新建 `tests/test_fock_bridge_f5.py`（不动 test_bridge.py）：
  - PNR 期望：`pnrd_probs` vs `|coherent_element|²` / `|squeezed_element|²` / `thermal_diag`（参数化，cutoff 选到 tail < 1e-9 并标注泄漏，atol 1e-7）
  - mean_photon 双表示：Gaussian 解析（½(⟨x²⟩+⟨p²⟩−1) / |α|² / sinh²r / n̄）vs Fock 数值
  - Threshold：Gaussian `p_click` vs Fock `1−pnrd_probs[0]`（coherent/squeezed/thermal）
  - 有损相干链：η ∈ {0.1,…,0.9} — Gaussian ⟨n⟩=η|α|²、p_click=1−e^{−η|α|²} vs Fock 数值（cutoff 40，α=0.8，atol 1e-7）
  - 泄漏纪律：所有参与比较的态断言截断 tail 低于容差（never-silent 规则的测试落地）
- R2: 新建 `tutorials/_build_08.py` + `tutorials/08_fock_bridge.ipynb`（mirror _build_05/07 模式，5 节）：
  ① 设定：同一物理实验的双表示搭建（GaussianState.coherent + FockState.coherent）
  ② Threshold 检测：p_click vs η 双曲线对账（Gaussian 解析 vs Fock 数值）
  ③ PNR 分布：Poisson vs 截断分布对比
  ④ 截断生存曲线：误差 vs cutoff/η/α（truncation engineering 叙事）
  ⑤ 结论：bridge 规则（Gauss→Fock 闭式、Fock→Gauss 容差内才成立）
  只 import 公共 API（cvsim.bridge + cvsim.fock + cvsim.gaussian），禁用 dq/DeepQuantum。
- R3: 零新公开 API（bridge.py/gaussian/fock 包零改动）；现有 923 测试保持绿。

## Acceptance Criteria

- [ ] 交叉核对套件全过：PNR/mean_photon/threshold 双表示一致（atol 1e-7，泄漏标注）
- [ ] 有损相干 η 扫掠：Gaussian vs Fock 全 η 点一致
- [ ] 泄漏纪律断言在（无静默比较）
- [ ] notebook 08 生成 + Run-All 通过；双表示结果对账 + 截断生存曲线
- [ ] `pytest -k fock` 全绿（218 + 新增）；`test_public_api.py`/`test_architecture.py` 零改动绿

## Out of scope

- Gaussian→Fock 完整状态转换（bridge.py ponytail：threshold 后验更新时需要）
- F6（SF interop）；新依赖（纯 numpy/scipy）
- 新公开 API（Q1 证据决定）

## Resolved decisions

- **Q1**: 零新公开 API — 现有面（bridge 元素² / pnrd_probs / p_click / vacuum_probability / mean_photon）已足够；证据：coherent/thermal 2.8e-16、squeezed 3.4e-8 纯泄漏驱动（2026-08-12 实测）
- **Q2**: 教程 = 有损相干态 η 扫掠（用户拍板 A）
- **Q3**: 新测试文件 `tests/test_fock_bridge_f5.py`（沿用 F1–F4 命名惯例）；notebook 编号 08（07 已占）

## Open questions

无（已收敛）。
