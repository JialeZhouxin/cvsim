# Bosonic B3 测量精度——homodyne CDF 网格反演精确采样

## Goal

将 Bosonic homodyne 采样从 B1 教学切"实峰池"（只取实 r̄ + Re(w)>0 分量，按 Re(w) 选峰再 `rng.normal`）升级为 **CDF 网格反演精确采样**，覆盖完整复权重混合 `P(x) = Σ_k w_k p_k(x)`，含干涉交叉项。条件化沿用现有精确 Born-rule 闭式（已处理复 r̄/复 w），sample 路径升级后自动受益。

物理事实源：`docs/vision-bosonic-simulator.md` §2.3 + §4-B3 + `docs/adr/0006` 决策 1。

## Background

- **现状（B1 教学切）**：`homodyne_sample`（`observables.py`）只从实 r̄ + Re(w)>0 分量池采样，忽略所有复 r̄/复 w 交叉干涉项。`homodyne_condition` 已是精确闭式（复 r̄/复 w，L may be complex）——B3 不动。
- **B3 目标**：替换 `homodyne_sample` 实现为 CDF 网格反演；新增 `homodyne_pdf` 工具函数供测试/教程核验。
- **为什么 CDF 反演**（ADR-0006）：`P(x) = Σ_k w_k p_k(x)` 中 w_k 是复数（干涉交叉项），混合无正概率权重 → 标准高斯混合采样/拒绝采样不可行（GKP 梳峰间 P→0，拒绝比爆炸）。CDF 网格反演是确定性、无拒绝、可测误差的唯一可行策略。

## Requirements

### R1 — `homodyne_sample` 替换为 CDF 网格反演

- 签名不变：`homodyne_sample(state, mode=0, phi=0.0, *, rng=None, n_grid=None, lim=None, shots=1000) -> np.ndarray`
- 返回值从 `float` 改为 `np.ndarray`（shape `(shots,)`）——CDF 反演天然批量，单 shot 调用返回 `array([x])`。
- 网格自动规则（`n_grid=None, lim=None` 时）：
  - `δx ≤ σ_min/5`（σ_min = 最窄对角分量 x_φ 标准差）
  - 范围 = 实部质心 ± 6σ（σ 取分量 x_φ 标准差的最大值，覆盖所有峰）
- override：`n_grid`/`lim` 非 None 时用指定值生成 `np.linspace(-lim, lim, n_grid)`。
- 采样：`rng.uniform(low, high, shots)` + `searchsorted(cdf, uniforms)` 向量化。
- **删旧实峰池逻辑**（`_POOL_IMAG_TOL` 过滤 + `rng.choice` 选峰 + `rng.normal`）。

### R2 — `homodyne_pdf` 新增工具

- `homodyne_pdf(state, mode=0, phi=0.0, *, n_grid=None, lim=None) -> tuple[np.ndarray, np.ndarray]`
- 返回 `(xs, P)`，`P = max(Re S, 0)`，`S(x) = Σ_k w_k p_k(x)`。
- 复权重混合：厄米共轭对闭合保证 Im(S)≈0；`is_hermitian`（B2）兜底核验。负 Re 值 = 非物理，warn 不抛错（采样用 max(Re,0)）。
- 网格规则同 R1（自动 + override）。
- 供测试交叉核对 + 教程可视化。

### R3 — `homodyne_sample_and_condition` 升级

- 现有实现 = `sample` + `condition` 薄组合。sample 升级后自动用精确路径。
- 签名补齐 override knob：`homodyne_sample_and_condition(state, mode=0, phi=0.0, *, rng=None, n_grid=None, lim=None, shots=1) -> tuple[np.ndarray, BosonicState]`。
- 取首个 sample outcome 调 condition（单态返回）。

### R4 — BOSONIC_PUBLIC 冻结纪律

- `homodyne_sample` / `homodyne_sample_and_condition` 名字不变，签名扩展（新增 n_grid/lim/shots kw）。
- `homodyne_pdf` 是新增名 → BOSONIC_PUBLIC 名单扩展（只增不减）。
- `homodyne_condition` / `homodyne_mean` / `homodyne_var` 不动。
- 所有教学切 docstring 标注移除（homodyne_sample 不再是教学切）。

## Constraints

- **物理事实源**：vision §2.3 + ADR-0006 决策 1。改采样策略必须先改 ADR + vision。
- **导入边界**（ADR-0001）：`cvsim/bosonic/*` 禁 import `cvsim.bridge`/`cvsim.wigner`/`cvsim.fock*`/兄弟 rep。Fock P(x) 交叉核对只在测试里调 `cvsim.fock`。
- **警告即错误**：`filterwarnings = ["error:cvsim.*"]`——warn 用 `warnings.warn`（非 cvsim 模块 warning 不触发 error；若触发则用 logging 或调测试过滤）。
- **依赖**：仅 numpy/scipy，无新依赖。
- **pytest marker**：注册 `phaseB3`。

## Acceptance Criteria

- [ ] **判据 1（cat 交叉核对）**：cat 态（even/odd）Bosonic `homodyne_pdf` vs Fock 高 cutoff（cutoff≥30）`_pdf_from_amps`，同 lim+n_grid 公共网格逐点 `|P_bosonic - P_fock| < atol=1e-7`。
- [ ] **判据 1（GKP 定性对齐）**：GKP `homodyne_pdf` 峰位/周期与 Fock 高 cutoff 定性对齐（无严格 atol，因无解析基准——ADR-0006）。
- [ ] **判据 2（Born 一致性，解析核验）**：网格上 `Σ_x P(x)·ρ_post(x)·δx ≈ ρ`，`ρ_post(x) = homodyne_condition(state, mode, phi, x)`，锁 `atol=1e-7`（cat/相干/热态）。
- [ ] **判据 3（采样直方图 vs 精确密度）**：10⁴ shots 分箱直方图 vs `homodyne_pdf` 归一化密度，bin 级相对误差 < 5%（cat 态，固定种子）。
- [ ] `phaseB3` marker 注册 + B3 测试全标。
- [ ] BOSONIC_PUBLIC 名单 +`homodyne_pdf`，`test_public_api.py` 冻结更新。
- [ ] 全套 pytest 绿（无回归）；B1/B2 专项无破坏。
- [ ] `homodyne_sample` 旧实峰池逻辑删除，docstring 不再标"teaching cut"。

## Open Items

- **GKP 网格爆炸风险**：ε→0 时 σ_min 极小，自动 `δx=σ_min/5` 可能给出 >10⁴ 网格点。出口判据实测时校准；必要时加 `max_grid` 上限 + 泄漏 warn（参考 B2 truncate 纪律）。B3 不预先实现，记为 vision §10 开放项。
