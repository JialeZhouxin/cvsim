# 对抗式审查与测试报告：`07-29-phase1-channel-general`

| 字段 | 内容 |
|------|------|
| 任务 ID | `phase1-channel-general` |
| 标题 | Phase1: F-CHANNEL-GENERAL Gaussian CPTP maps |
| 状态 | completed（2026-07-29） |
| 审查角色 | 研究员 / 对抗式审查 |
| 审查日期 | 2026-07-29 |
| 代码基线 | `cvsim/gaussian/channels.py`, `cvsim/gaussian/__init__.py`, `tests/test_gaussian_channels.py` |

---

## 1. 任务完成了什么

本任务实现 vision 文档中的 **F-CHANNEL-GENERAL**：通用的 Gaussian CPTP 通道 `(X, Y, d)`，以及三个命名预设（`loss`、`amplifier`、`phase_noise`），全部统一路由到 `apply_gaussian_channel`。

### 1.1 交付物清单

| 能力 | API | 位置 |
|------|-----|------|
| 通用 Gaussian CPTP 通道 | `apply_gaussian_channel(state, X, Y, d=None, *, validate=True)` | `cvsim/gaussian/channels.py` |
| CP 检查 | `is_cp_channel(X, Y, *, atol=1e-10)` | 同上 |
| CP 校验（抛错） | `validate_channel(X, Y, *, atol=1e-10)` | 同上 |
| 损耗 / 衰减器 | `loss(state, T, mode=None, nbar=0.0)` | 同上 |
| 相位无关放大器 | `amplifier(state, G, mode=None, nbar=0.0)` | 同上 |
| 相位扩散 | `phase_noise(state, sigma, mode=None)` | 同上 |
| 作用模式解析 | `_acted_block`（内部） | 同上 |
| 模块导出 | `cvsim.gaussian` 与 `cvsim.gaussian.channels` | `__init__.py` |
| 测试 | `tests/test_gaussian_channels.py`（32 项） | tests |

### 1.2 数学模型（已实现）

单步 Gaussian 通道：

$$
\bar r \mapsto X\bar r + d,\qquad V \mapsto X V X^{\mathsf T} + Y
$$

代码在每次更新后做对称化 `V = 0.5 * (V + V.T)`，与既有 `loss` 行为一致。

### 1.3 命名预设（代码实现）

| 预设 | 每作用模的 $X$ | 每作用模的 $Y$ | 约束 |
|------|----------------|----------------|------|
| `loss(T, nbar=0)` | $\sqrt{T}\,I_2$ | $(1-T)(\bar n + \tfrac12)\,I_2$ | $0\le T\le 1$, $\bar n\ge 0$ |
| `amplifier(G, nbar=0)` | $\sqrt{G}\,I_2$ | $(G-1)(\bar n + \tfrac12)\,I_2$ | $G\ge 1$, $\bar n\ge 0$ |
| `phase_noise(sigma)` | $e^{-\sigma^2/2}\,I_2$ | $(1-e^{-\sigma^2})\tfrac12\,I_2$ | $\sigma\ge 0$ |

`phase_noise` 采用 **PRD 推荐的 Option B**：随机相位旋转 $R(\phi)$ 按 $\phi\sim\mathcal N(0,\sigma^2)$ 平均。这与 Strawberry Fields / MrMustard 的 `phase_noise` 形式一致（等效于 $T=e^{-\sigma^2}$ 的 loss-like 通道）。

### 1.4 明确不在本任务范围（PRD Out）

- `GaussianCircuit.amplifier` / `.phase_noise` DSL 挂载（后续 follow-up）
- 显式相关多模 loss（当前仅通过 `(X,Y)` 支持；相关 `loss` 多模列表是 P1+）
- F-ANALYSE 信息量（熵、保真度、log-neg）
- Phase1 exit 教程 “interferometer + loss + homodyne”

### 1.5 对 PRD Acceptance 的对照

| # | 验收项 | 结果 |
|---|--------|------|
| 1 | `X=S`, `Y=0`, `d=0` 与 `apply_symplectic` 逐位一致 | **通过** |
| 2 | `loss(T=1)` 恒等；`loss(T=0, nbar=0)` 作用模真空 | **通过** |
| 3 | 既有 `loss` 教程/测试数字无回归 | **通过**（240 项全绿） |
| 4 | 纯 loss 族通过 `validate_channel`；非法 `Y` 失败 | **通过** |
| 5 | 放大器 $G>1$ 对相干态 $\langle n\rangle \to G|\alpha|^2$ | **通过** |
| 6 | 相位噪声：$\sigma=0$ 恒等；$\sigma>0$ 抑制非对角；CP 通过 | **通过** |
| 7 | 通道复合定律 $X=X_2X_1$, $Y=X_2Y_1X_2^{\mathsf T}+Y_2$ | **通过** |
| 8 | `validate=True` 拒绝非 PSD CP；`validate=False` 作为可信逃逸舱 | **通过** |
| 9 | 全量 pytest 通过；新增 `test_gaussian_channels.py` | **通过**（240 项） |

**结论（完成度）：** PRD 中所有 P0 Phase-1 验收项均已落地，核心数学实现正确。

---

## 2. 对抗式审查

审查策略：不默认信任已有单测，从 **CP 条件正确性 / 约定一致性 / 预设物理 / 数值极限 / API 信任边界 / 规格漂移** 六个方向施压。

### 2.1 数学正确性（高置信）

| 检查 | 方法 | 结果 |
|------|------|------|
| CP 条件尺度 | 对纯 loss / 放大器 / 相位噪声族，代码使用 $\Omega/2$ | 全部通过 |
| 纯 loss 族 $T\in[0,1]$ | `is_cp_channel` | 全部通过 |
| 量子受限放大器族 $G\ge 1$ | `is_cp_channel` | 全部通过 |
| 相位噪声族 $\sigma\ge 0$ | `is_cp_channel` + `is_physical` | 全部通过 |
| 非 CP 拒绝 | $X=1.5I,Y=0$；$X=2I,Y=0$；$Y=-0.1I$ | 全部拒绝 |
| 单元极限 | $X=S$ 辛矩阵，$Y=0$, $d=0$ ≡ `apply_symplectic` | max err $\sim 10^{-16}$ |
| 复合定律 | 两通道顺序 vs 一步 $(X_2X_1, X_2Y_1X_2^{\mathsf T}+Y_2)$ | max err $\sim 10^{-16}$ |
| loss+amplifier 复合 | 预设链 vs 显式 $(X,Y)$ | max err $\sim 10^{-16}$ |
| 热 loss 光子数 | $T|\alpha|^2 + (1-T)\bar n$ | 精确到机精 |
| 放大器光子数 | $G|\alpha|^2 + (G-1)$（量子限） | 精确到机精 |
| 相位噪声非对角抑制 | 旋转挤压态后施加大 $\sigma$ | $|V_{01}|$ 单调下降 |
| 大 $\sigma$ 极限 | 相干态 → 真空 | 通过（atol $10^{-5}$） |
| 大增益数值稳定 | `amplifier(G=1e6)` 仍物理 | 通过 |

**判定：** 核心通道语义在 xxpp、$\hbar=1$、$V_{\text{vac}}=I/2$ 约定下正确，未发现会破坏 Gaussian 物理性的实现级 bug。

### 2.2 重大规格漂移：CP 条件公式缺少 $1/2$

**发现：** PRD（第 23 行）与 `docs/vision-gaussian-simulator.md`（第 428 行）给出的 CP 条件为

$$
Y + i\Omega - i X\Omega X^{\mathsf T} \succeq 0
$$

而代码实现（`is_cp_channel`）与 `validate_channel` 错误消息实际使用

$$
Y + i\frac{\Omega}{2} - i X\frac{\Omega}{2}X^{\mathsf T} \succeq 0
$$

更严重的是，`apply_gaussian_channel` 的 **docstring**（第 74 行）也写成 bare-$\Omega$ 形式，与内部实现不一致。

**为什么代码是对的（而文档是错的）：**

项目 hard convention 为 $V_{\text{vac}}=I/2$，对应不确定性关系 $V + i\Omega/2 \succeq 0$。取纯 loss $T=0.5, \bar n=0$：
- 代码的 $X=\sqrt{0.5}I$, $Y=(1-0.5)/2 \cdot I$ 通过 CP 检查。
- 若用 bare-$\Omega$ 公式，$H = 0.25I + i(1-0.5)\Omega$ 的特征值为 $-0.25$ 和 $0.75$，会把一个合法的纯 loss 通道误判为非 CP。

**对抗验证：**

```text
Bare-Omega CP check for code Y=(1-T)/2:
  T=0.0: eigs=[-0.5  1.5], PSD=False
  T=0.5: eigs=[-0.25  0.75], PSD=False
  T=0.75: eigs=[-0.125  0.625], PSD=False
  T=1.0: eigs=[0. 0.], PSD=True
```

**影响：** 这是一个 **文档与实现不一致** 的 defect，但不是正确性 blocker（代码实现自洽且物理正确）。若用户/贡献者按 PRD/vision 字面公式复现，会得到错误结论。

### 2.3 预设通道审查

#### `loss`

- 行为与既有实现完全一致：$T=1$ 恒等，$T=0,\bar n=0$ 真空。
- 热环境支持正确：$\langle n\rangle_{\text{out}} = T|\alpha|^2 + (1-T)\bar n$。
- `mode=None` 默认全部模式；单模时其他块完全不变。
- 通过 `apply_gaussian_channel(..., validate=False)` 跳过冗余 CP 校验，合理。

#### `amplifier`

- $G=1$ 恒等；$G>1$ 正确放大并加噪声。
- 量子限默认 $\bar n=0$ 符合 PRD。
- 对真空态：$\langle n\rangle = G-1$，正确。

#### `phase_noise`

- Option B（旋转平均）实现与 PRD 推荐一致。
- 位移按 $e^{-\sigma^2/2}$ 衰减，符合随机旋转平均的直观。
- 大 $\sigma$ 时协方差趋于 $I/2$、位移趋于 0。

**对抗观点：** `phase_noise` 名字容易让人联想到“只加 p 方向噪声”或 Ornstein-Uhlenbeck 动态模型。实现选择的是 **静态随机相位平均**（一种 CPTP 映射），并非动态扩散方程的连续时间极限。docstring 已说明模型；审查期间已将 `docs/vision-gaussian-simulator.md` 中对应 open question 标记为已解决并选定 static random-phase average。

### 2.4 API 与鲁棒性

| 点 | 行为 | 评价 |
|----|------|------|
| 默认校验 CP | 非 CP / 形状错 → `ValueError` | 好 |
| `validate=False` | 允许非 CP 输入；可能输出非物理态 | 逃逸舱必要，但 **静默破坏物理性**；仅限内部信任路径 |
| 参数越界 | `T\notin[0,1]`、`G<1`、$\bar n<0$、$\sigma<0$、mode 越界均抛错 | 好 |
| `d` 形状错 | 抛错 | 好 |
| `mode` 类型 | 仅 `int | None` 暴露给预设；内部 `_acted_block` 支持 `list/range` 但未公开 | 功能窄于内部能力，不影响 P0 |
| `apply_gaussian_channel` 的 `d` | positional-or-keyword；`validate` keyword-only | 符合 Python 习惯 |
| `is_cp_channel` 对非方阵/奇数维 | 返回 `False` 而非抛错 | 与 `is_physical` 一致，可接受 |
| 未改动既有 `GaussianCircuit.loss` | DSL 仍可用 | 无回归 |

### 2.5 规格 / 文档漂移汇总

| 来源 | 表述 | 实现 | 严重度 |
|------|------|------|--------|
| PRD §CP condition | $Y + i\Omega - i X\Omega X^{\mathsf T} \succeq 0$ | 代码用 $\Omega/2$；**已修正 PRD** | **高（已修）** |
| Vision §F-CHANNEL-GENERAL | 同上 bare-$\Omega$ | 代码用 $\Omega/2$；**已修正 vision** | **高（已修）** |
| `apply_gaussian_channel` docstring | bare-$\Omega$ | 代码用 $\Omega/2$；**已修正 docstring** | **高（已修）** |
| Vision §phase-noise | OU vs static 未决 | 已实现 static random-phase average；**已标记为已解决** | **中（已修）** |
| PRD `phase_noise` 签名 | `mode=None` | 一致 | 可接受 |
| PRD `amplifier` nbar | quantum-limited default $\bar n=0$ | 一致 | 可接受 |
| PRD Out | Circuit DSL 未挂载 | `GaussianCircuit` 无 `.amplifier`/`.phase_noise` | 符合 Out |

### 2.6 设计优点

1. **统一通道抽象：** 三个预设全部路由到 `apply_gaussian_channel`，避免三套独立实现。
2. **CP 检查封装良好：** `is_cp_channel` 可独立使用，测试/调试方便。
3. **信任边界清楚：** 命名预设内部构造的 `(X,Y)` 保证 CP，故 `validate=False`；用户通用通道默认严格校验。
4. **约定一致：** 与 `cvsim.gaussian.analyse.is_physical` 共用 $\Omega/2$ 尺度。
5. **向后兼容：** 既有 `loss` 数字无变化，240 项 pytest 全绿。

### 2.7 缺陷与风险登记

| ID | 级别 | 描述 | 建议 |
|----|------|------|------|
| R1 | **高（已修）** | PRD/vision/docstring 的 CP 公式缺少 $1/2$，与实现不一致 | 已修正 `apply_gaussian_channel` docstring、`docs/vision-gaussian-simulator.md`、`.trellis/tasks/archive/2026-07/07-29-phase1-channel-general/prd.md` |
| R2 | **中（已修）** | `phase_noise` 文档仍暗示 OU vs static 未选定 | 已更新 `docs/vision-gaussian-simulator.md` 为已选定的 random-phase-average 模型 |
| R3 | 中 | 预设 `loss/amplifier/phase_noise` 仅支持单模或全模，未暴露 `list/range` | PRD 未要求，但内部 `_acted_block` 已支持；如需要可公开 |
| R4 | 低 | `validate=False` 可产生非物理态 | 文档已标明 trusted escape hatch；可在 debug 模式加 warn |
| R5 | 低 | Circuit DSL 未挂载 amplifier/phase_noise | PRD Out；作为 follow-up 跟踪 |
| R6 | 低 | `is_cp_channel` 对非方阵返回 `False` 而非抛错 | 与 `is_physical` 一致，但错误消息在 `validate_channel` 中统称“non-CP”，形状问题不够明确 |

**未发现：** CP 检查尺度错误、预设物理性破坏、复合定律失败、loss 回归等 *blocking* 缺陷。

### 2.8 对抗式结论

| 维度 | 评分（1–5） | 说明 |
|------|-------------|------|
| 数学正确性 | 5 | 通道更新、CP 检查、复合定律均正确 |
| 与 PRD 功能符合度 | 5 | 验收项全过 |
| 与 PRD/vision 文档符合度 | 4.5 | CP 公式已对齐；仅 phase-noise 文档和预设签名细节仍有轻微漂移 |
| API 完成度 | 4.5 | 核心+导出齐；DSL 未做（Out） |
| 测试充分度（原库） | 4 | 主路径覆盖好；缺大参数压力、相关 Y 等 |
| 可维护性 | 4.5 | 代码清晰；审查中已修正 docstring 与 vision/PRD 公式 |
| **总评** | **通过** | 功能可用、数学正确；R1 文档漂移已在审查中修复 |

---

## 3. 测试报告

### 3.1 原有回归

```text
pytest tests/test_gaussian_channels.py -v
32 passed
```

| 用例 | 意图 | 结果 |
|------|------|------|
| `test_channel_unitary_matches_apply_symplectic` | 单元通道等价 | PASS |
| `test_channel_shape_mismatch` | 形状错误 | PASS |
| `test_channel_d_displacement` | 位移向量 $d$ | PASS |
| `test_cp_pure_loss_family_passes` | 纯 loss CP | PASS |
| `test_cp_amplifier_family_passes` | 放大器 CP | PASS |
| `test_cp_phase_noise_family_passes` | 相位噪声 CP | PASS |
| `test_cp_rejects_negative_Y` | 非法 Y 拒绝 | PASS |
| `test_cp_rejects_unphysical_X` | 非法 X 拒绝 | PASS |
| `test_validate_true_rejects_non_cp` | 默认校验 | PASS |
| `test_validate_false_escape_hatch` | 逃逸舱 | PASS |
| `test_loss_t1_identity` | loss 恒等 | PASS |
| `test_loss_t0_vacuum` | loss 真空 | PASS |
| `test_loss_coherent_photon_scales` | loss 光子缩放 | PASS |
| `test_loss_single_mode_leaves_other` | 单模隔离 | PASS |
| `test_loss_thermal_nbar` | 热 loss | PASS |
| `test_loss_rejects_bad_T_nbar` | 参数校验 | PASS |
| `test_loss_mode_out_of_range` | 越界 | PASS |
| `test_amplifier_g1_identity` | 放大器恒等 | PASS |
| `test_amplifier_coherent_photon_scales` | 放大器光子缩放 | PASS |
| `test_amplifier_quantum_limited_adds_half` | 真空放大噪声 | PASS |
| `test_amplifier_thermal_nbar` | 热放大 | PASS |
| `test_amplifier_rejects_bad_G` | 参数校验 | PASS |
| `test_amplifier_single_mode_leaves_other` | 单模隔离 | PASS |
| `test_phase_noise_sigma0_identity` | 相位噪声恒等 | PASS |
| `test_phase_noise_damps_squeezed_offdiag` | 相干抑制 | PASS |
| `test_phase_noise_large_sigma_to_vacuum` | 大噪声极限 | PASS |
| `test_phase_noise_rejects_negative_sigma` | 参数校验 | PASS |
| `test_phase_noise_single_mode_leaves_other` | 单模隔离 | PASS |
| `test_channel_composition_law` | 复合定律 | PASS |
| `test_loss_then_amplifier_compose` | loss→amplifier 复合 | PASS |
| `test_loss_all_modes_default` | 全模默认 | PASS |
| `test_amplifier_all_modes_default` | 全模默认 | PASS |

全量回归（防相邻模块回归）：

```text
pytest tests -q
240 passed
```

### 3.2 对抗 / 研究员测试

脚本：`tests/_adversarial_channel_review.py`  
运行：`PYTHONPATH=. py -3 tests/_adversarial_channel_review.py`

```text
TOTAL: 31 PASS, 0 FAIL / 31
```

> 注：在审查过程中发现 `apply_gaussian_channel` docstring 使用 bare-$\Omega$ 公式；已当场修正为 $\Omega/2$，因此 F1 由 FAIL 转为 PASS。

#### 分组摘要

**A. CP 条件与数学约定（5）** — 全过  
- A1: 纯 loss 族通过代码 CP 检查
- A2: bare-$\Omega$ 公式会拒绝合法纯 loss（证明文档公式错误）
- A3: 非 CP 通道被拒
- A4: `validate_channel` 抛错消息含正确公式
- A5: 单元通道 $X=S,Y=0$ ≡ `apply_symplectic`

**B. 预设通道（9）** — 全过  
- loss 恒等/真空/光子缩放/热环境/单模隔离
- amplifier 恒等/光子趋势/热环境/单模隔离
- phase_noise 恒等/相干抑制/大噪声极限/阻尼因子/单模隔离

**C. 复合定律（3）** — 全过  
- 两通用通道复合
- loss→amplifier 复合
- 热 loss→热 amplifier 复合

**D. API 鲁棒性（4）** — 全过  
- `validate=True` 拒绝非 CP
- `validate=False` 逃逸舱
- 形状不匹配抛错
- 坏参数（$T$、$G$、$\bar n$、$\sigma$、mode 越界）全部拒绝

**E. 多模与物理性（5）** — 全过  
- `mode=None` 与逐个模式等价
- 单模通道不触碰未作用块
- 相关 $Y$（全 2m）CP 且物理
- 大增益数值稳定

**F. 文档 / 规格漂移（1）** — 全过（docstring 已修正）
- F1: `apply_gaussian_channel` docstring 现在包含正确的 $\Omega/2$ 公式

### 3.3 审查期间已修复项

**F1 — docstring 公式错误（已修）**

`apply_gaussian_channel` 的 docstring 原写：

```python
``Y + iΩ − i XΩXᵀ ≽ 0``.
```

已修正为：

```python
``Y + iΩ/2 − i XΩXᵀ/2 ≽ 0``
```

**仍需修复：** PRD（`.trellis/tasks/archive/2026-07/07-29-phase1-channel-general/prd.md`）和 `docs/vision-gaussian-simulator.md` 中的 bare-$\Omega$ 公式。

### 3.4 原测试缺口（审查后建议补的单测）

`test_gaussian_channels.py` 覆盖主路径，但建议长期补：

1. **CP 条件尺度显式测试**：验证 bare-$\Omega$ 会误判合法通道（把 F1 的发现固化成回归测试）。
2. **多模 `apply_gaussian_channel` 全矩阵**：当前测试主要用单模或对角 $Y$；加一个非对角 $Y$（如相关噪声）的 CP/物理性测试。
3. **大 $G$ / 大 $\sigma$ 数值烟雾**：防止未来浮点退化。
4. **`is_cp_channel` 形状边界**：非方阵、奇数维、X/Y 形状不一致。
5. **`validate=False` 产生非物理态** 的显式断言（作为文档化行为）。

---

## 4. 总体结论

### 4.1 一句话

**`07-29-phase1-channel-general` 正确实现了通用 Gaussian CPTP 通道 `(X,Y,d)` 与 loss/amplifier/phase_noise 三个命名预设，数学与物理性在对抗测试下稳定，PRD 功能验收项全部满足。审查中发现并修复了 PRD、vision 与 `apply_gaussian_channel` docstring 中 CP 公式缺少 $1/2$ 因子的文档漂移。**

### 4.2 建议行动项

| 优先级 | 行动 |
|--------|------|
| ✅ 已做 | 修正 `cvsim/gaussian/channels.py` 中 `apply_gaussian_channel` docstring |
| ✅ 已做 | 修正 `.trellis/tasks/archive/2026-07/07-29-phase1-channel-general/prd.md` 中的 CP 公式 |
| ✅ 已做 | 修正 `docs/vision-gaussian-simulator.md` 中的 CP 公式并标记 phase-noise 决策为已解决 |
| P2 | 若需多模列表支持，将预设 `mode` 签名扩展为 `int \| Sequence[int] \| None`（内部 `_acted_block` 已支持） |
| P2 | Circuit DSL：`GaussianCircuit.amplifier` / `.phase_noise` |
| P3 | 将 §3.4 中的缺口项精简并入 `tests/test_gaussian_channels.py` |
| P3 | Phase1 总出口：补 “interferometer + loss + homodyne” 教程 |

### 4.3 审查签字意见

- **功能合并 / 使用：** 批准（代码实现正确）
- **视为“文档已与实现零漂移”：** 批准（R1 已修复）
- **视为“Circuit DSL 已完成”：** 不批准（PRD Out）

---

## 附录 A — 关键代码锚点

```text
cvsim/gaussian/channels.py
  is_cp_channel
  validate_channel
  apply_gaussian_channel
  _acted_block
  loss
  amplifier
  phase_noise

cvsim/gaussian/__init__.py           # 公开导出
cvsim/gaussian/analyse.py            # is_physical (Ω/2 约定)
cvsim/gaussian/state.py              # GaussianState
cvsim/conventions.py                 # omega
tests/test_gaussian_channels.py
tests/_adversarial_channel_review.py
tests/test_thermal_loss.py           # loss 回归
.trellis/tasks/archive/2026-07/07-29-phase1-channel-general/prd.md
docs/vision-gaussian-simulator.md    # F-CHANNEL-GENERAL
```

## 附录 B — 最小复现

```bash
# 单元测试
PYTHONPATH=. py -3 -m pytest tests/test_gaussian_channels.py -v

# 全量回归
PYTHONPATH=. py -3 -m pytest tests -q

# 对抗套件
PYTHONPATH=. py -3 tests/_adversarial_channel_review.py

# 研究员快速检查：CP 公式尺度
PYTHONPATH=. py -3 - <<'PY'
import numpy as np
from cvsim.conventions import omega
from cvsim.gaussian import is_cp_channel

T = 0.5
X = np.sqrt(T) * np.eye(2)
Y = (1 - T) * 0.5 * np.eye(2)
print("code CP check:", is_cp_channel(X, Y))  # True

O = omega(1)
H_bare = Y + 1j * O - 1j * (X @ O @ X.T)
w = np.linalg.eigvalsh(0.5 * (H_bare + H_bare.conj().T))
print("bare-Omega eigs:", w)  # contains negative!
PY
```

## 附录 C — 运行环境快照

```text
platform win32
Python 3.14.0
pytest 9.0.2
numpy 2.x

tests/test_gaussian_channels.py: 32 passed
tests (full suite): 240 passed
tests/_adversarial_channel_review.py: 31 PASS, 0 FAIL
```
