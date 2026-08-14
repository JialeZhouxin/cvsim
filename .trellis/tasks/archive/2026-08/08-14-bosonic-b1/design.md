# Bosonic B1 — 实现设计

> 架构层约束见 `08-14-bosonic-architecture/design.md`（A1–A12）。本文件只落 B1 文件级设计。

## 1. 文件变更

| 文件 | 变更 |
|------|------|
| `cvsim/bosonic/state.py` | +`coherent(alpha, nmode=1, mode=0)` 工厂；+`weight_sum`（自 observables 迁入） |
| `cvsim/bosonic/gates.py` | +`fourier`/`mach_zehnder`/`cz`/`cx`/`interferometer`（薄封装 symplectic S_*，`validate_u` 透传） |
| `cvsim/bosonic/channels.py` | +`amplifier`/`phase_noise`（复用 `_loss_XY` 的 X,Y 构建模式 → 抽 `_channel_XY` 风格私有 helper） |
| `cvsim/bosonic/observables.py` | 删除 homodyne 块（迁 measure.py）；保留 `mean_photon` + `_as_real` 等私有 helper（供 measure.py import） |
| `cvsim/bosonic/measure.py` | **新建**：homodyne 全套 re-export（`from .observables import ...`，实现单一来源）+ `heterodyne_sample/heterodyne_condition/heterodyne_sample_and_condition` + `p_click/sample_threshold/measure_threshold` |
| `cvsim/bosonic/gkp.py` | `gkp_logical_overlap` docstring + DeprecationWarning |
| `cvsim/bosonic/__init__.py` | 新 `__all__` = BOSONIC_PUBLIC 冻结清单；homodyne/heterodyne/threshold 从 measure.py 出 |
| `tests/test_public_api.py` | +BOSONIC_PUBLIC 冻结块（镜像 FOCK 块样式） |
| `tests/test_b1_bosonic_*.py` | 新增 phaseB1 marker 测试 |

## 2. 数学与语义

### 2.1 门（K=1 对齐）

全部 = `apply_symplectic(state, S_*(...))`，签名 1:1 复制 Gaussian `gates.py`：
- `fourier(state, mode=0)` = `phase(π/2)`
- `mach_zehnder(state, m1, m2, theta, phi=0)` → `S_mach_zehnder`
- `cz(state, weight, m1, m2)` → `S_CZ`；`cx` → `S_CX`
- `interferometer(state, U, *, validate_u=True)` → `S_from_unitary(U, validate=validate_u)`

### 2.2 通道

逐分量 `V_k ← X V_k Xᵀ + Y, r̄_k ← X r̄_k`，权重不动，对称化 V（loss 现成模式）：
- `amplifier(state, G, mode=None, nbar=0)`：`X=√G·I, Y=(G−1)(nbar+½)·I`（per acted mode）
- `phase_noise(state, sigma, mode=None)`：`damp=e^{−σ²/2}, X=damp·I, Y=(1−damp²)·½·I`

### 2.3 heterodyne（混合态）

- **sample**：逐分量边缘 `(μ_k, Σ_k) = (r̄_k[ixp], V_k[ixp,ixp] + I/2)`；混合分布 `P(z)=Σ_k w_k N(z; μ_k, Σ_k)` 是**实正权重高斯混合**（Σ_k 仅来自 V_k 实部对角块，权重 w_k 此处取实部？）—— **注意**：混合 heterodyne 边缘与 homodyne 不同，Σ w_k N(z; μ_k, Σ_k) 中 μ_k 含虚部（交叉分量 r̄ 虚 → μ_k 复），N 的二次型 `(z−μ)ᵀΣ⁻¹(z−μ)` 复数化。**诚实处理（B1 教学切）**：sample 用实对角池（同 homodyne 教学切，`imag_tol` 过滤），K=1 精确；混合态精确采样留给 B3 同款 CDF 策略。condition 用**全分量**（复 μ 二次型展开为实：`(z−Re μ)ᵀΣ⁻¹(z−Re μ) − (Im μ)ᵀΣ⁻¹(Im μ)`？）—— 不：Q 函数对复位移的实形式 = `N(z; Re μ, Σ)` 与 `N(z; Im μ 修正)` 需推导。
  - **B1 范围决策**：heterodyne condition 教学切 = 只处理实对角分量条件化（同 homodyne_condition 现状哲学），交叉分量权重按真空重叠近似？—— **否，过度工程**。B1 锁定：heterodyne **sample + condition 均按实对角分量池**（教学切，显式标注），K=1 与 Gaussian 严格对齐（B1 exit 2 只测 K=1）；混合态 heterodyne 精确化与 B3 同批（CDF 策略）。文档诚实标注。
- **condition**：对池内分量逐个跑 Gaussian `heterodyne_condition` 公式（V_B', r̄_B', 删模），权重 `w_k ∝ w_k·N(z; μ_k, Σ_k)`（实高斯密度），归一化 Σw=1；K=1 → 与 Gaussian 逐位一致。

### 2.4 threshold（outcome-only）

- `p_click(state, mode=0)`：`1 − Σ_k w_k · vacuum_probability(V_k, r̄_k, mode)`（`cvsim.bridge.vacuum_probability` 现成，复 r̄ 二次型复数化 → 和取实部 + 虚部容差检查 `_as_real`）；K=1 与 Gaussian `p_click` atol 对齐
- `sample_threshold(state, mode=0, *, rng)`：`bernoulli(p_click)`
- `measure_threshold`：本任务只出 sample_threshold（circuit 版本属 B5）

### 2.5 空态语义（heterodyne 删模尾部）

单模 K=1 heterodyne condition → 0 模态（对齐 Gaussian `nmode=0`）。`BosonicState.nmode` 对空组件改返回 `0`（现抛 ValueError；无现存依赖，grep 确认仅 state.py/gates.py 内部）。gates `_nmode` 保持抛错（对空态应用门 = 用户错误）。

### 2.6 工厂

`coherent(alpha, nmode=1, mode=0)`：V=vac, r̄=√2·(Re α, Im α) 在 (mode, nmode+mode)，w=1 —— 等价 `displace(BosonicState.vacuum(nmode), alpha, mode)`，直构免门开销。

## 3. 兼容

- homodyne 从 observables → measure：`__init__` 改从 measure.py import；observables 内实现保留（B3 前单一实现源），外部 import 路径 `cvsim.bosonic.homodyne_*` 不变
- `weight_sum` observables → state：`__init__` re-export 不变
- 现有测试（test_b1_bosonic_gates/test_m3_bosonic 等）零改动通过
- `api-stability.md` §2.2 注明 cvsim.bosonic 从"教学面"升级为"B1 冻结面"（doc amend，minor）

## 4. 测试设计（phaseB1 marker）

| 文件 | 覆盖 |
|------|------|
| `tests/test_b1_bosonic_gates.py`（扩展） | 新增 5 门 K=1 vs Gaussian atol；cz/cx 辛性；interferometer U 校验拒绝非酉 |
| `tests/test_b1_bosonic_channels.py` | amplifier/phase_noise K=1 vs Gaussian atol；G<1/σ<0 拒绝；T=1/σ=0 恒等 |
| `tests/test_b1_bosonic_measures.py` | heterodyne K=1 sample 分布（seeded 统计）+ condition 态等价（nmode=0）；threshold p_click K=1 vs Gaussian atol + 混合态（cat）p_click ∈ [0,1] 实部 + 虚部≈0 |
| `tests/test_public_api.py` | BOSONIC_PUBLIC 冻结块 |
| 回归 | homodyne re-export 后现有 bosonic 测试全绿；全套 pytest |

## 5. 风险

- heterodyne 混合态是教学切（实对角池）—— 与 B3 精确化边界划清，docstring 标注，防被当生产用
- threshold 真空重叠对复 r̄ 分量的复数值：虚部容差检查必须严格（>1e-8 抛错），防静默丢干涉
