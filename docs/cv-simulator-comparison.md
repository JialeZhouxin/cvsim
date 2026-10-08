# cvsim vs 其他 CV 高斯模拟器：功能对照与差距

> 检索/实证日期：2026-10-04 · 方法：**装库直接 introspect 真实 API**，不读文档二手转述。
> 探针脚本：scratch（会话期临时，不入库）。版本钉死：

| 库 | 版本 | 安装 | 说明 |
|---|---|---|---|
| **cvsim** | 本仓库 | 项目 `.venv` | numpy，Gauss+Fock+Bosonic 教学/生产 MVP |
| **Strawberry Fields** | 0.23.0 | py3.11 + `scipy<1.14` + `setuptools<81` | Xanadu 全栈 CV 库，三后端 |
| **Piquasso** | 8.0.1 | py3.13（numba 需 `NUMBA_DISABLE_JIT=1` 才能 import） | 匈牙利 Wigner 中心，四模拟器 + 三连接器 |
| **MrMustard** | 0.7.3 | py3.11（0.7.3 是最后带 wheel 的版本；1.x 需 tf，无 wheel） | Xanadu 可微/Bargmann，全参数可训练 |

> MrMustard 新版（1.x，完整相空间/Bargmann 表示）装不上（拉 tensorflow，只到 cp311 wheel）。本文 MrMustard 结论**只对 0.7.3**。

---

## 1. 门/指令集对照（实测 introspect）

### 1.1 cvsim 三后端核心白名单

| backend | 数量 | ops |
|---|---|---|
| **gaussian** | 16 | amplifier, beamsplitter, cx, cz, displace, fourier, gaussian_channel, interferometer, loss, measure_heterodyne, measure_homodyne, mz, phase, phase_noise, squeeze, two_mode_squeeze |
| **fock** | 15 | gaussian 去掉 fourier/gaussian_channel/interferometer/mz，加 **kerr, mach_zehnder, measure_pnr** |
| **bosonic** | 17 | gaussian + mach_zehnder + **measure_threshold** |

Lab 侧 UI 隐藏（core 有，`/run` 返 422）：`mach_zehnder`（Lab 用 `mz`）、`measure_threshold`（仅 bosonic 暴露）。

### 1.2 Strawberry Fields 0.23.0（63 项）

| 类别 | 项 |
|---|---|
| 制备 | Vacuum, Fock, Coherent, Squeezed, DisplacedSqueezed, Thermal, **Catstate**, **GKP**, **GraphEmbed**, **BipartiteGraphEmbed** |
| 门 | Sgate, S2gate, Dgate, Rgate, BSgate, MZgate, Fourier, Interferometer, CXgate, CZgate, **CKgate**, **Kgate**(Kerr), **Vgate**(cubic), **Pgate**(shear), Ggate |
| 通道 | LossChannel, **ThermalLossChannel**, PassiveChannel |
| 测量 | MeasureFock, MeasureHD, MeasureHomodyne, MeasureHeterodyne, MeasureP, **MeasureThreshold**, MeasureX |
| 引擎 | `fock`(tf), `gaussian`, `bosonic`(Kerr/cubic/GKP 用) |

### 1.3 Piquasso 8.0.1

| 类别 | 项 |
|---|---|
| 制备 | Vacuum, NumberState, Thermal, StateVector, DensityMatrix, **Graph**, BatchPrepare |
| 门 | Beamsplitter(5050), Displacement, **Position/MomentumDisplacement**, Squeezing, Squeezing2, Phaseshifter, Fourier, Interferometer, **LossyInterferometer**, MachZehnder, **Kerr, CrossKerr, CubicPhase, SNAP, QuadraticPhase** |
| 通道 | Attenuator, **Loss, UniformLoss**, DeterministicGaussianChannel |
| 测量 | ParticleNumberMeasurement, Homodyne, Heterodyne, **Generaldyne**, ThresholdMeasurement, **ImperfectParticleNumberMeasurement**, PostSelectPhotons, ImperfectPostSelectPhotons |
| 模拟器 | PureFockSimulator(矢量), FockSimulator(密度矩阵), GaussianSimulator(协方差), PassiveSimulator, SamplingSimulator(弃) |
| 连接器 | NumpyConnector, **JaxConnector, TensorflowConnector** |
| 批量 | BatchApply, BatchPrepare |

### 1.4 MrMustard 0.7.3

| 类别 | 项 |
|---|---|
| 制备 | Vacuum, Coherent, SqueezedVacuum, DisplacedSqueezed, Thermal, TMSV, Fock, **Gaussian**, State |
| 门 | Dgate, Rgate, Sgate, S2gate, BSgate, Pgate(相位器), MZgate, CXgate, CZgate, Interferometer, **RealInterferometer**, Ggate |
| 通道 | **Attenuator, Amplifier, AdditiveNoise, PhaseNoise**（透射率/增益/nbar 均为**可训练参数**） |
| 测量 | PNRDetector, ThresholdDetector, Homodyne, Heterodyne, **Generaldyne**（均带 efficiency/dark_counts 可训练） |
| 编排 | Circuit |
| 训练 | training.Optimizer, TensorboardCallback；每个门每个参数都有 `*_trainable` / `*_bounds` |
| 数学 | math.Categorical（非高斯条件采样）, physics.wigner |

---

## 2. 能力矩阵（cvsim 视角）

| 能力 | cvsim | SF 0.23 | Piquasso 8.0.1 | MrMustard 0.7.3 |
|---|:---:|:---:|:---:|:---:|
| Gaussian 协方差表示 | ✅ | ✅ | ✅ | ✅ |
| Fock（截断矢量/密度矩阵） | ✅ | ✅ | ✅（双模拟器） | ✅ |
| Bosonic（cat/GKP） | ⚠️ 部分 | ✅ 完整 | ⚠️ | ❌ |
| 非高斯门（Kerr/cubic/SNAP） | ❌ | ✅ | ✅ | ❌（0.7.3） |
| 光子损失/热化通道 | ✅ | ✅ | ✅ | ✅ |
| 相位噪声通道 | ✅ | ❌ | ❌ | ✅ |
| 放大器通道 | ✅ | ❌ | ❌ | ✅ |
| 零差/外差测量 | ✅ | ✅ | ✅ | ✅ |
| PNR 计数测量 | ✅(fock 后端) | ✅ | ✅ | ✅ |
| 阈值探测器 | ✅(bosonic 后端) | ✅ | ✅ | ✅ |
| **测量条件化（后选择）** | ✅ | ✅ | ✅（但有缺陷¹） | ⚠️ |
| **前馈 feedforward** | ✅ | ✅ | ✅ | ❌（0.7.3 无此 API） |
| **GBS 采样（Hafnian）** | ⚠️ 薄适配² | ✅(`apps.sample`) | ✅ | ❌ |
| **图嵌入（GraphEmbed）** | ❌ | ✅ | ✅(`Graph`) | ❌ |
| Wigner 函数 | ✅ | ✅ | ✅ | ✅ |
| 纠缠判据（log-neg/PPT） | ✅ | ❌³ | ⚠️³ | ❌³ |
| **可微分 / 梯度后端** | ✅ **jax**⁵（gauss+fock，函数式） | ⚠️ tf **仅 Fock 引擎**⁷ | ✅ jax/tf 连接器（`custom_gradient`） | ✅ tf + `training.Optimizer` |
| **GPU 加速** | ❌ | ⚠️ | ✅(cuQuantum) | ⚠️ |
| **批量执行** | ❌ | ⚠️⁴ | ✅(`BatchApply`) | ❌ |
| **变分训练 / 优化器** | ✅⁶ `cvsim.optim.minimize`（Adam / SGD + 停止判据） | ⚠️ `apps.train.VGBS`（变分 GBS，非通用优化器） | ✅ | ✅✅ `training.Optimizer`（4 个 lr 分参数类型 + Tensorboard） |
| **应用层（qchem/图算法）** | ❌ | ✅(`clique/subgraph/similarity/points/qchem/vibronic`) | ⚠️ | ❌ |
| 扫描（参数扫） | ✅ | ⚠️ | ⚠️ | ⚠️ |
| 本地 UI + HTTP API | ✅✅ 独有 | ❌ | ❌ | ❌ |
| 单一 IR（JSON schema） | ✅ 独有 | ⚠️(Blackbird) | ⚠️(指令) | ⚠️ |

¹ Piquasso `PureFockSimulator` 在「通道后接任何指令」时崩（`state_vector` 属性缺失，见 `docs/piquasso-oracle-qualification.md §4`）。**没有任何 Piquasso 后端同时提供「Fock + 通道 + 零差」。**
² cvsim 的 `pnr_probs` / `gbs_sample` / `threshold_sample` 是 The Walrus 薄封装（`cvsim.gaussian.walrus`），可选 extra `cvsim[gbs]`，未装时抛 `RuntimeError`。**自有 Hafnian 内核 = 无。**
³ 实测：SF 的 `state` 方法表无 `log_negativity`（只有 `fidelity`/`purity` 类），整个 `strawberryfields.backends.states` 无 `neg` 相关名；Piquasso 无 `log_negativity`（只有 `get_purity`/`fidelity`）；MrMustard 0.7.3 只有 `purity`。**`log_negativity` 是 cvsim 内建、三家都要自己写的功能。**
⁴ SF 的 `Engine.run(program, *, args, compile_options)` **无电路级 batch 参数**；批量只出现在 `apps.sample.sample(A, n_mean, n_samples)` 的采样层面。Piquasso 的 `BatchApply`/`BatchPrepare` 是真正的电路级批量。
⁵ cvsim 的 AD 是**已完成功能**（vision Phase 4 / F4，2026-08-10/12）：`cvsim/backend.py`（唯一 jax 感知点，懒加载）→ `cvsim/symplectic.py` 19 函数 `backend=` 参数化 → `cvsim/ad.py`（高斯链：`apply_gaussian` + `log_neg_loss`）+ `cvsim/fock_ad.py`（Fock 链：`squeeze_u`/`bs_u`/`kerr_diag`/`cat_fidelity`/`bs_overlap`），加 `tutorials/05_ad_designer.ipynb`、`07_fock_ad_designer.ipynb`。实测（2026-10-04）`jax.grad` 对 TMSV 的 dE_N/dr == 解析值 2/ln2，相对误差 6.8e-11。可选 extra `[jax]`，核心 import 路径零 JAX。
⁶ cvsim **现在有**一个最小优化器（2026-10-04 起）：`cvsim/optim.py` 的 `minimize(f, x0, optimiser="adam"|"sgd", lr=..., max_steps=..., grad_tol=..., f_tol=...)`，手写 Adam + 朴素 SGD（可选动量），接受任意 pytree 参数与**逐参数学习率**，返回带 `converged`/`reason`/`history`/`grad_norm_history` 的 `Result` dataclass。零新依赖（不引 optax）。**关键设计**：`f_tol` 默认关（设计目标平顶，小 Δf 不等于小梯度）；`converged` 只在真判据满足时为 `True`，`max_steps` 与发散分别报 `reason="max_steps"` / `"diverged"`，绝不冒充收敛。对照：SF 的 `apps.train` 实测只有 `VGBS`/`Exp`/`KL`/`Stochastic` 等变分 GBS 组件，**无通用优化器**（`optimize`/`Optimizer` 不存在）；Piquasso 无；MrMustard 的 `training.Optimizer` 是最完备的（4 个分类型 lr + `TensorboardCallback` + 每门每参数 `*_trainable`/`*_bounds`），仍是**唯一带训练框架**的。所以「有优化器」已不是独有，**「参数对象化的训练框架」**才是。
⁷ cvsim 的 AD 覆盖 **gaussian + fock** 两条链，`cvsim/bosonic/` 零 backend 引用（无 AD）。对照：SF 的 tf 后端**只接 Fock 引擎**（`tfbackend` 全文件 42 处 `Fock`、0 处 `bosonic`，Gaussian 后端 0 处 tf 引用），SF 的高斯/bosonic 路径亦无 AD。**所以这一格 cvsim 不落后，是「双方都未覆盖 Bosonic AD」。**

---

## 3. 差距定级

### 3.1 结构性差距（对方有、cvsim 无，且非「薄适配」能补）

| # | 能力 | 谁有 | 对 cvsim 的意义 |
|---|---|---|---|
| G1 | **参数级（stateful）可微 API** | MrMustard（每门每参数 `*_trainable`/`*_bounds` 原生字段）、SF/Piquasso（引擎级后端切换） | cvsim 的 AD 是**函数式**的：`backend="jax"` 传参 + `jax.grad` 包住自己的目标函数（⁵）。缺的不是梯度，是「把参数做成可训练对象」的 API 层——MrMustard 是此形态标杆。 |
| G2 | **参数对象化的训练框架** | **MrMustard 独有**（`training.Optimizer`，4 个分类型 lr + Tensorboard + 每门每参数 `*_trainable`/`*_bounds`） | cvsim 已有最小优化器（`cvsim.optim`，⁶，Adam/SGD + 停止判据 + 轨迹），但**参数是函数式的**：pytree 传进 `minimize`，不是「门对象自带 `trainable` 字段」。无目标函数基类、无 callback/TensorBoard。SF/Piquasso 亦无通用优化器。 |
| G3 | **GPU 加速** | Piquasso(cuQuantum) | Piquasso 已把高斯+非高斯搬上 GPU。cvsim 纯 numpy。 |
| G4 | **非高斯门（Kerr/cubic/SNAP/CrossKerr）** | SF、Piquasso | cvsim 仅在 Fock 截断层有 `kerr`，无 cubic/SNAP/CrossKerr。vision 标「远期」。 |
| G5 | **图嵌入 / GBS 应用层** | SF(`apps.sample/clique/qchem`)、Piquasso(`Graph`) | 最大团、分子振动谱、点云配准等。cvsim 无。 |
| G6 | **完整 Bosonic（GKP/cat 制备）** | SF | cvsim bosonic 有 gkp/cat 模块，但无 SF `GKP`/`Catstate` 制备 op 的完备度。 |
| G7 | **电路级批量执行** | Piquasso(`BatchApply`/`BatchPrepare`) | cvsim `/batch` 是 fock-only 端点，非通用批量语义。SF 亦无（只在采样层）。 |

### 3.2 cvsim 领先 / 独有

| # | 能力 | 说明 |
|---|---|---|
| C1 | **统一 IR + JSON schema + HTTP API + 本地 UI** | 三家都是 Python 库，无此工作台形态。`circuit_v1` schema 单点声明，palette/whitelist 自动派生。 |
| C2 | **三后端白名单一致性锁** | `test_lab_backend_symmetry.py` 等把「core op 加了但 whitelist 没跟」的漂移钉死（三家无此概念）。 |
| C3 | **纠缠判据 + 物理性校验内建** | `log_negativity` / `duan_sum` / `is_physical` / `validate_state` / `validate_channel` 直接可呼。 |
| C4 | **相位噪声 / 放大器通道双覆盖** | SF 无 phase_noise、无 amplifier；Piquasso 无 phase_noise。cvsim 三家之外仍有覆盖。 |
| C5 | **golden byte-frozen 纪律** | 9 条 golden 未重捕，R-A2 锁 API 稳定性。 |

### 3.3 名义差距、实则对等或更好（不必补）

| 项 | 结论 |
|---|---|
| 零差/外差条件化 | cvsim 已有 `homodyne_sample_and_condition` / `heterodyne_sample_and_condition`，**且 Piquasso 在「通道+条件化」这格反而是坏的** → cvsim 在此格**更强**。 |
| Hafnian 内核 | vision §1.3 明确「不要替换 The Walrus」——薄适配是**设计选择**，非缺口。 |
| 本地 UI | 三家视为非目标。cvsim 的 Lab 是差异化资产。 |

---

## 4. 结论

**cvsim 的定位不是「又一个 CV 模拟器」，而是「单一 IR + 三表示一致 + 可交互工作台」。**

- **门/测量覆盖度**：与 SF/Piquasso 相比，**Gaussian 侧已齐**（唯一缺口是图嵌入与非高斯门）。
- **真实差距**：参数对象化训练框架（G2）、GPU（G3）、非高斯与应用层（G4/G5）。**注意：可微分本身 cvsim 已有**（jax，gauss+fock 两链，实测梯度对解析值 6.8e-11）；**优化器也已补上**（`cvsim.optim`，⁶）；缺的是 MrMustard 那种「门对象自带 `trainable` 字段 + callback」的 API 形态（G1/G2）。
- **一处反超**：Piquasso 的「通道 + 条件化」是坏的，cvsim 是好的——**cvsim 在这格比头部库更可靠**。
- **一处设计取舍**：Hafnian 走 The Walrus 薄适配，是 vision 明示的「不自造重轮子」，**不算差距**。
- **两处反超（新发现）**：`log_negativity` 与 `duan_sum` 三家都不内建（SF/Piquasso/MrMustard 都要自己写）；cvsim 直接可呼。

### 若要补齐，优先级建议

1. **G5 图嵌入**（`GraphEmbed` 是 GBS 全部应用层的入口，代码量小、杠杆大）
2. **G1 参数级可微 API**（不是造梯度——梯度已有；是把 `*_trainable` 形态包上去）
3. **G4 非高斯门**（Fock 层已有 `kerr`，加 cubic/SNAP 是延伸而非重构）
4. 训练框架封装（G2：参数对象化 + callback/Tensorboard；优化器本体已有）、GPU 加速（G3）（工程量大，收益依赖规模，最低优先）

---

## 5. 复现

```powershell
# 三家各装一个一次性 venv（不要装进项目 .venv）
uv venv $env:TEMP\cvprobe-sf --python 3.11
uv pip install --python $env:TEMP\cvprobe-sf\Scripts\python.exe "strawberryfields==0.23.0" "scipy<1.14" "setuptools<81"

uv venv $env:TEMP\cvprobe-pq --python 3.13
uv pip install --python $env:TEMP\cvprobe-pq\Scripts\python.exe piquasso
# 运行前：$env:NUMBA_DISABLE_JIT="1"（否则 numba JIT 加载 LLVM 崩）

uv venv $env:TEMP\cvprobe-mm --python 3.11
uv pip install --python $env:TEMP\cvprobe-mm\Scripts\python.exe "mrmustard==0.7.3"
```

## 6. 相关

- `docs/gaussian-simulator-literature.md` —— 理论文献与软件生态（含 Wayo 2025 综述 #16）
- `docs/piquasso-oracle-qualification.md` —— Piquasso 作 oracle 的资格认证 + 13 条约定坑
- `docs/sf-roundtrip.md` / `docs/sf-roundtrip-fock.md` —— SF 约定映射
- `docs/vision-gaussian-simulator.md` —— Phase C/D（可微分）解锁条件
- `cvsim/gaussian/walrus.py` —— GBS 互操作适配层
- `docs/optical-operations-gap-inventory.md` —— 姊妹文档：cvsim 三表示 **对照现实光学全集** 的缺口盘点（本文是对照**其他软件**，那篇是对照**物理**，互补）
- `docs/GBS.md` / `docs/gbs-walrus.md` —— GBS 与 The Walrus 细节
