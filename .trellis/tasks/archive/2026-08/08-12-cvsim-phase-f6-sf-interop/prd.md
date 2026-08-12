# PRD — Phase F6: SF interop + density export

## Goal

Vision §4 F6（`docs/vision-fock-simulator.md` F6 节）：Fock ↔ Strawberry Fields 互操作 — round-trip golden 测试（无运行时依赖）+ 互操作文档（mirror `docs/sf-roundtrip.md`）+ 密度矩阵导出格式文档化。

## Vision 原文要求（F6 退出判据）

1. Round-trip golden tests（no runtime dep on external tools）。
2. Interop docs with copy-paste scripts（mirror `docs/sf-roundtrip.md`）。
3. （Build 行）density-matrix export format documented。

## Background（已确认事实，2026-08-12 实证）

- **SF 可运行**（临时 venv `/tmp/sfenv`）：SF **0.23.0** + thewalrus 0.22.0（fock backend 的 D/S/BS/S2/K/R 矩阵全部来自 thewalrus）；scipy>=1.15 需 `simps→simpson` shim；setuptools<81（pkg_resources）。
- **Fock 基约定全部对齐**（实证：walrus displacement(r,phi) 与解析 Poisson 完全一致；Engine 干净实例下 Dgate(0.3,0.4) ket = 解析相干态）：

| 门 | SF（fock backend） | cvsim fock | 对应关系 |
|---|---|---|---|
| D | `Dgate(r, phi)` = D(re^{iφ}) | `displace(state, alpha)` | alpha = r e^{iφ} |
| S | `Sgate(r, phi)` = S(re^{iφ}) | `squeeze(state, r)`（实 r） | SF phi=0 |
| BS | `BSgate(θ, φ)` = exp[θ(e^{iφ}a₀†a₁ − e^{−iφ}a₀a₁†)] | `beamsplitter(state, θ, φ)` 同式 | 逐位相同 |
| S2 | `S2gate(r, phi)` = exp(ζa†b† − ζ*ab) | `two_mode_squeeze(state, r)`（实 r） | SF phi=0 |
| R | `Rgate(φ)` = exp(iφa†a) | `phase(state, θ)` | θ=φ |
| K | `Kgate(κ)` = exp(iκa†²a²) | `kerr(state, χ)` | χ=κ |

- **Fock 基幺正与 ħ 无关**（D/S/BS/S2/K/R 矩阵元只含 α/ζ/θ，无 ħ）→ 无 Gaussian 侧的 2.0/√2 缩放问题；仅需相位/幅度逐位比对。
- **密度导出格式**：`FockDensity.rho` = (N^m, N^m) complex，多模 C-order（`amps.reshape(N,N)` ravel）→ 与 SF `state.dm()`（同 C-order 展平）直接对照。
- **已知陷阱（实证踩坑）**：SF `Engine("fock")` 实例**复用残留状态**（Dgate 结果被前一个 prog 污染）→ golden 脚本每个 prog 必须新建 Engine。
- Gaussian 侧先例：`docs/sf-roundtrip.md`（70 行 copy-paste 脚本 doc）；`cvsim/interop/ordering.py` 已有（Gaussian 专用，F6 不动）。

## Requirements

- R1: `tools/gen_sf_golden.py` — 一次性生成 golden（SF venv 运行，脚本头记录 SF/thewalrus 版本 + 生成日期；含 simps shim + setuptools<81 说明）→ `tests/_golden/sf_fock_golden.npz`
- R2: `tests/test_sf_golden_f6.py` — golden 对照（numpy 读 npz，**不 import SF**，无 SF 运行时依赖）：
  - 态制备：vacuum / Fock(1) / Fock(1,1) / coherent α=0.5e^{0.7i}
  - 单模门：S(0.5)|0⟩、D(0.4,0.3)|0⟩、R(0.6)|1⟩、K(0.1)|1⟩
  - 双模门：BS(π/4, 0.2)|1,1⟩、S2(0.5)|0,0⟩
  - 复合链（同一物理实验）：2 模 S(0.4)→D→BS(θ,φ)→K 全程
  - 密度：thermal n̄=1.0 → FockDensity.rho vs SF dm()（导出格式直接对照）
  - 全**复数幅度**比对（相位是 F6 核心风险），atol 1e-9（SF fock float64）
- R3: `docs/sf-roundtrip-fock.md` — mirror 70 行风格：约定表 + copy-paste 脚本（cvsim→SF、SF→cvsim 双向）+ 密度导出格式（rho 序、dm() 对照）+ 陷阱（Engine 复用残留、cutoff、重归一化、ħ 无关性）
- R4: vision-fock F6 状态节更新（v0.5.0）
- R5: 零既有代码改动（fock/gaussian/bridge/interop 全不动）；FOCK_PUBLIC 冻结零影响；全套件保持绿

## Acceptance Criteria

- [ ] golden 生成脚本可复现（SF venv + 文档化版本）；npz 提交入库
- [ ] 对照套件全过：7 组 golden 复数幅度 atol 1e-9；测试无 SF import
- [ ] `pytest tests/ -q` 全套件绿（959 + 新增）
- [ ] docs 双向 copy-paste 脚本 + 密度导出格式 + 陷阱完整
- [ ] vision-fock v0.5.0 状态同步

## Out of scope

- SF 运行时依赖（optional extra 不新增；golden 静态对照）
- Gaussian SF interop（已存在 `docs/sf-roundtrip.md`）；`cvsim/interop` 扩展
- F7+ 阶段；GKP 互操作

## Resolved decisions

- **Q1**（golden 来源）：SF venv 一次性生成真实 golden（thewalrus 是 SF fock backend 的数值引擎，非自证循环）；npz 提交，测试零依赖
- **Q2**（版本固定）：golden 脚本头记录 SF 0.23.0 / thewalrus 0.22.0 + 日期；npz 内嵌 metadata
- **Q3**（范围）：7 组对照（态 4 + 门 6 + 复合链 + 密度），全部复数幅度比对

## Open questions

无（证据驱动收敛）。
