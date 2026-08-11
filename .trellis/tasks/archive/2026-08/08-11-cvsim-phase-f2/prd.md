# F2 — Fock analyse + measure + api-freeze

来源：ADR-0004 / `08-10-cvsim-fock-arch/design.md` §3.5–3.8 / vision-fock-simulator §4 F2。
前置：F1（工厂/门/通道全 public，822 绿）。

## 目标

Fock 能力面继续镜像高斯：测量（PNR condition + heterodyne）、analyse 四函数、
通用 m 密度、F2 出口 API 冻结。

## 切片

1. **f2-measure**：`pnr_sample/pnr_condition/pnr_sample_and_condition` +
   `heterodyne_condition/heterodyne_sample(_and_condition)`（observables.py）。
   heterodyne = 相干态 POVM |β⟩⟨β|/π；1 模纯态后验恒 = |β⟩（秩 1 投影性质）；
   2 模条件化保留另一模。sample 对齐 homodyne 的离散网格 PDF 风格（Q 函数网格）。
   不做 heterodyne mean（design 锁）。
2. **f2-analyse**：新建 `cvsim/fock/analyse.py`：`entropy_vn/log_negativity/
   fidelity/partial_trace`（镜像 gaussian/analyse 命名；Fock 直接谱，非 symplectic）。
   - entropy_vn：密度谱 −Σλ ln λ（纯态 0）
   - log_negativity：PT 谱 Σ|λ| → ln（TMS 高斯对照）
   - fidelity：纯-纯 |⟨ψ|φ⟩|²；密度 Uhlmann √ρσ√ρ
   - partial_trace(state, keep)：2 模归约（einsum 通用 m）
3. **f2-generic-m**：FockDensity 通用 m（m≥1 任意，cutoff = d^{1/m} 整数校验）；
   FockState ndim 校验放宽；gates/channels 对 m>2 显式拒绝（诚实边界，稀疏 F3）。
   partial_trace/entropy 自然通用。
4. **f2-apifreeze**：`FOCK_PUBLIC` 镜像 `GAUSSIAN_PUBLIC`（test_public_api.py 模式）；
   导出面冻结。

## Exit 条件

- 全 public + docstring 数学式（leakage 沿用 F1 三件套纪律）
- 测试锚：fidelity coherent α vs β = e^{−|α−β|²}；log_neg TMS vs 高斯闭式；
  entropy thermal 闭式；partial_trace 乘积态
- pytest 全量绿（822 基线）+ test_architecture allowlist
- 每切片独立 commit + OCR 收口

## 非目标（F3+）

- FockCircuit/compile（F3）、稀疏表示、backend=/AD（F4）、桥转正（F5）、SF interop（F6）
