# Design — Phase F6: SF interop + density export

## 目标与边界

Fock ↔ SF fock backend 互操作：golden 对照测试（零运行时依赖）+ 互操作文档 + 密度导出格式。
零既有代码改动 — 纯新增：1 生成脚本 + 1 测试文件 + 1 npz + 1 doc。

## 架构

### 1. `tools/gen_sf_golden.py` — golden 生成器（SF venv 一次性）

- 脚本头 docstring：用法（`uv venv` + `uv pip install "strawberryfields" "setuptools<81"`）、SF 0.23.0 / thewalrus 0.22.0 版本锁、生成日期。
- 运行时前置：`import scipy.integrate as si; if not hasattr(si,'simps'): si.simps = si.simpson`（scipy>=1.15 shim）。
- **每个 prog 新建 `sf.Engine("fock", backend_options={"cutoff_dim": N})`**（复用残留实证陷阱）。
- **golden 全存 dm（复数密度矩阵）**：SF 0.23 fock backend 对 `Fock(1)` 预备态返回 `pure=False` → `ket()` 为 None（实证）；dm 保相对相位，且顺带覆盖密度导出格式对照。
- **cutoff 分层（实证泄漏扫描决定）**：squeezed@50（S(0.5) 泄漏 tanh^cutoff 回流，@40 仍 3e-8；@50 6.0e-10）、displaced@12（7.6e-11）、rotated/kerr/bs/s2@10（0.0 / 2.4e-16）、s2_00@30（3.6e-11）、chain@45（1.7e-11）、thermal@10（0.0）。生成一次性 ~70s（含 import 编译 7.3s）。
- **BS 相位映射（实证）**：cvsim `beamsplitter(θ,φ)` ≡ SF `BSgate(−θ,−φ)`（全张量 max|Δ|=1.1e-16 @ (−θ,−φ)；+θ,+φ 差 1.39）→ golden 用 SF 原值 `BSgate(π/4, 0.2)`，测试侧 cvsim 用 `beamsplitter(−π/4, −0.2)`，docs 约定表写映射。
- 输出 `tests/_golden/sf_fock_golden.npz`（dm 展平 C-order，complex128）：
  - `squeezed_r05` (10×10) — S(0.5)|0⟩ dm
  - `displaced` (12×12) — D(0.4,0.3)|0⟩ dm
  - `rotated` (10×10) — R(0.6)|1⟩ dm；`kerr` (10×10) — K(0.1)|1⟩ dm
  - `bs_11` (100×100) — BS(π/4,0.2)|1,1⟩ dm
  - `s2_00` (900×900) — S2(0.5)|0,0⟩ dm（@30）
  - `chain` (2025×2025) — 2 模 S(0.4)→D(0.3,0.2)@m0、D(0.2,0.5)@m1、BS(0.8,0.4)、K(0.1)@m1 dm（@45）
  - `thermal_dm` (10×10) — thermal n̄=1.0 dm（`prepare_thermal_state` → `state.dm()`）
  - `metadata` (str) — JSON：SF/thewalrus/scipy 版本、日期、各项 cutoff 与参数
- 生成脚本自检：SF dm 概率对角 vs cvsim 概率粗对齐（打印），再保存。

### 2. `tests/test_sf_golden_f6.py` — 对照套件（无 SF import）

- `np.load("tests/_golden/sf_fock_golden.npz")`（路径相对测试文件，`Path(__file__).parent / "_golden"`）。
- 对照：
  - squeezed: `FockDensity.from_pure(FockState.squeezed(50, 0.5)).rho` vs golden（phi=0 默认）
  - displaced: `FockDensity.from_pure(displace(FockState.vacuum(12), 0.4*np.exp(1j*0.3)))`
  - rotated: `FockDensity.from_pure(phase(FockState.fock(1, 10), 0.6))`
  - kerr: `FockDensity.from_pure(kerr(FockState.fock(1, 10), 0.1))`
  - bs_11: `FockDensity.from_pure(beamsplitter(FockState.fock2(1,1,10), −π/4, −0.2))`（BS 映射）
  - s2_00: `FockDensity.from_pure(two_mode_squeeze(FockState.vacuum(30, 2), 0.5))`
  - chain: `FockDensity.from_pure(同序 cvsim 门 @45)`
  - thermal_dm: `FockDensity.thermal(10, 1.0).rho`
- 全部**复数 dm 逐位比对**（相对相位保留；`assert_allclose` atol=1e-9）；每项测试 docstring 标注 SF 版本 + 生成日期 + cutoff。

### 3. `docs/sf-roundtrip-fock.md` — 互操作文档（mirror sf-roundtrip.md 70 行风格）

1. 表格：cvsim Fock ↔ SF fock backend 门对应（D/S/BS/S2/R/K + 态制备 Vacuum/Fock/Coherent/Thermal）
   - **BS 映射：cvsim `beamsplitter(θ,φ)` = SF `BSgate(−θ,−φ)`（实证全张量 1.1e-16）**
2. 核心事实：**Fock 基幺正 ħ 无关**（vs Gaussian 的 2.0/√2 缩放链）— 只需逐位比对
3. 转换链 copy-paste：cvsim→SF（读 ket 写 SF 初始化？SF 无"加载任意 ket"API — 说明 golden 路线：SF 为基准，cvsim 对照；反向用 `state.ket()/dm()` 导出）
4. 密度导出格式：`FockDensity.rho` (N^m, N^m) complex C-order = `dm()` 展平；示例：thermal/cat 态导出 + SF 侧读法
5. 陷阱：Engine 复用残留（实证）、cutoff/重归一化、scipy simps shim、版本锁、`np.math` 移除
6. 如何重新生成 golden（脚本 + 命令）

### 4. vision-fock 状态节

- Status: F1–F6 complete；F6 节标注 done；gap 表 Interop 行更新；文档控制 +0.5.0 行。

## 兼容性

纯新增文件；无签名/行为变化；`cvsim/interop` 不动（Gaussian 专用）。

## 风险与回滚

- 风险：SF 版本漂移导致 golden 与未来 SF 不一致 → 版本锁 + 生成日期 + 重新生成脚本；测试只依赖 npz 不依赖 SF
- 风险：相位约定细节（BS 的 e^{±iφ} 符号、Kerr 符号）→ golden 生成时双端各跑一次，生成脚本内自检（SF 端概率 vs cvsim 端概率先粗对齐，再全复数）
- 回滚：单 commit 纯新增
