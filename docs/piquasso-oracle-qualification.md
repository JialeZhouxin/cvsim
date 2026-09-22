# Piquasso 作为外部 oracle 的资格认证（步骤 0 结论）

> 状态：**已完成资格认证（spike）**。结论：piquasso 8.0.1 **可以**作为 cvsim Fock 侧"非高斯 + 测量条件化"的外部参考，但**不能**覆盖"通道（loss/amp/dephasing）+ 条件化"这一格——那是它当前版本的实现缺陷。
>
> 证据脚本：`tools/qualify_piquasso_oracle.py`（43 项闭式判据，全通过）。本文档是它的结论与约定映射表。

## 1. 为什么做这一步

cvsim 的外部 oracle 缺口不是"单门算错"——单门早就用手推闭式钉到 1e-12 了。缺的是两件事：

1. **Fock 复合/通道/测量条件化**（3+ 模链、loss/amp/noise、PNR/homodyne 后验）——`tests/_golden/sf_fock_golden.npz` 完全不覆盖（8 例，≤2 模，无通道，无测量）。
2. **Bosonic/GKP 数值可信度**。

在让任何外部库当 oracle 之前，必须先用**我们自己已经信的闭式**锤它。未经资格认证的 oracle 比没有 oracle 更坏：它会制造假的信心。

## 2. 环境（实测）

| 项 | 值 |
|---|---|
| piquasso | **8.0.1** |
| numpy | 2.5.3 |
| scipy | 1.18.1 |
| Python | 3.13.5 |
| 安装 | `uv pip install piquasso`（有 C++ 扩展 wheel，无需编译器） |

与项目 `uv.lock` 的 numpy 2.5.1 / scipy 1.18.0 同代，**无版本冲突**。Python 支持 3.10–3.14，与 `pyproject.toml` 的 `>=3.10,<3.15` 和 CI 矩阵完全对齐。

## 3. 资格认证结果：43 项闭式判据全通过

判据分三档，全部对上：

### 3a. 约定钉死（1e-14，精确）

| 判据 | 结果 |
|---|---|
| 真空 `xxpp_covariance_matrix` == cvsim `2V` == `I` | 精确 |
| 压缩 `S(0.5)` 的 `xxpp_cov == diag(e^-1, e^+1)` | 1.1e-16 |
| 相干态 `xxpp_mean_vector == rbar = √2·(Re α, Im α)` | 2.2e-16 |

**结论：`Config(hbar=1)` 下，piquasso 的 xxpp 协方差/均值恰好等于 cvsim 的 `2V` / `rbar`，零缩放因子。**

### 3b. 单门闭式（1e-12，精确）

相干态 PNR（Poisson）、压缩真空 PNR（`sech r·(2n)!/(4ⁿ(n!)²)·tanh^{2n}r`，奇数项严格为 0）、热态 PNR（`n̄ⁿ/(n̄+1)^{n+1}`）、loss on |1⟩（`ρ₀₀=1−T`、`ρ₁₁=T`）、HOM（`P(1,1)=0`、`P(2,0)=P(0,2)=1/2`）、TMSV joint（`p(n,n)=tanh^{2n}r/cosh²r`）、Kerr 相位——**全部 1e-12 内通过**。

### 3c. 测量条件化（这是缺口本体，2e-3 量级为统计误差）

| 判据 | 类型 | 误差 |
|---|---|---|
| TMSV 后选择 `n₀=k` → 剩余模**恰好** `\|k⟩` | 精确（shots=None） | **3.9e-33** |
| 后选择概率 == `tanh^{2k}r/cosh²r` | 精确 | 4.4e-16 |
| joint PNR + homodyne：`Var(x₁\|n₀=k) == (2k+1)/2` | 统计 20 万次 | 9.8e-4 … 1.4e-2 |
| joint 边缘 `P(n₀=k)` == 闭式 | 统计 | 3.4e-4 … 2.6e-3 |
| `\|k⟩` homodyne 方差 `(2k+1)/2` | 统计 4 万次 | 3.8e-3 … 1.2e-2 |

**结论：piquasso 的条件化在闭式上精确复现。它挣到了"可被相信"的资格。**

## 4. 发现的真实缺陷（必须记录，决定能力边界）

**`PureFockSimulator` 在"通道之后接任何后续指令"时崩溃**：

```
AttributeError: 'FockState' object has no attribute 'state_vector'
  at piquasso/_simulators/fock/pure/simulation_steps/utils.py:63
     in _get_remaining_state_vector
```

最小复现：任意 `Attenuator` → 任意后续指令（`ParticleNumberMeasurement`、`HomodyneMeasurement`、甚至另一条 `Beamsplitter`）。

这不是用法问题，是源码问题——`_get_remaining_state_vector` 无条件访问 `state.state_vector`，而通道会把纯态 `PureFockState` 换成密度矩阵态 `FockState`：

```python
def _get_remaining_state_vector(state, subspace_basis, modes):
    index = get_projection_operator_indices(...)
    return state.state_vector[index]     # 混合态没有这个属性
```

**两个后端的算力是互斥的**：

| 模拟器 | 通道（loss/amp） | homodyne | PNR 中途测量 |
|---|---|---|---|
| `PureFockSimulator` | 状态会变混合态 | 支持 | 支持 |
| `FockSimulator`（密度矩阵） | 支持 | **完全不支持**（`InvalidSimulation`） | 支持 |
| `GaussianSimulator` | 支持 | 支持 | 只在末尾，且采样是 `(值, 权重)` 对 |
| `SamplingSimulator`/`PassiveSimulator` | 部分 | 不支持 | 支持 |

`pq.simulate()` 自动选择救不了：它会选到不接受"中途 PNR"的那一个。

**没有任何一个后端同时提供「Fock 路径 + 通道 + homodyne」。**

绕行路线全部失败（已实测）：
- `DensityMatrix` 重新注入 → 该指令在 `PureFockSimulator` 上未实现
- 先通道后测量（两段程序）→ `PureFockSimulator` 仍崩
- `FockSimulator` 扛通道 → homodyne 不支持

**所以缺陷不是"少一个功能"，而是恰好落在 cvsim 最想要的那一格上。**

## 5. 能力边界：piquasso 能覆盖什么、不能覆盖什么

| cvsim 缺口 | piquasso 可用？ | 说明 |
|---|---|---|
| 3+ 模 Fock 链（无非高斯） | ✅ | `PureFockSimulator`，cutoff 可调 |
| 非高斯复合（Kerr/CrossKerr/SNAP/CubicPhase）+ PNR + homodyne | ✅ | 实测 3 模 Kerr+BS+PNR+homodyne 通过 |
| PNR 后选择 / 条件化 | ✅ **精确** | 1e-12 |
| Feedforward（测量结果 → 后续门参数） | ✅ | `lambda x: 0.1*x[0]` 按分支解析，实测确认 |
| **通道（loss/amp/noise）+ 条件化** | ❌ | 实现缺陷，见 §4 |
| 通道 + 只做 PNR | ⚠️ 半 | 只有 `FockSimulator` 能跑，无 homodyne |
| 通道本身（Gaussian 路径） | ✅ | 但 cvsim 的 Gaussian 侧已全闭式覆盖，外部参考**边际价值为零** |

## 6. 约定映射表（用之前必须钉死，全部实测）

这些坑我在认证过程中全部踩过一遍，误报为"piquasso 算错"，实际是我读错了约定。**不写下来就会重踩。**

| # | 坑 | 正确做法 |
|---|---|---|
| P1 | **`Config.hbar` 默认是 2.0**，不是 1 | 每个 `Config` 显式写 `hbar=1` |
| P2 | `Vacuum()` 之后再来 `NumberState(...)` 是**叠加相加**（norm 变 2），不是替换 | 用 `NumberState` 单独准备，别先 `Vacuum()` |
| P3 | homodyne 采样标度在两后端不同：`PureFock` 方差 = `hbar/2`；`Gaussian` 方差 = `hbar` | **`PureFockSimulator` 的 homodyne 样本 == cvsim 的 xxpp 坐标**，无 √2 因子 |
| P4 | `GaussianSimulator` 多测量样本是 `(值, 权重)` **成对**的 | 取 `t[0]`；无权重的 `.var()` 无意义（权重可达 ±4 万） |
| P5 | `Attenuator(theta)` 的透射率是 **`T = cos²θ`**，不是 `T` 直传 | `theta = arccos(sqrt(T))` |
| P6 | **Fock 模拟器不隐式初始化真空**，`Displacement` 单独跑得到全零态（norm=0） | 显式 `pq.Q(...) \| pq.Vacuum()` 或 `NumberState` |
| P7 | `FockState`（混合态）没有 `mean_photon_number()` / `state_vector` | 从 `fock_probabilities` 或 `density_matrix` 取 |
| P8 | 占据数序 1.0.0 起从字典序改为**反字典序** | 用 `fock_probabilities_map`，别用扁平索引 |
| P9 | `pq.StateVector` 已弃用 | 用 `NumberState(occupation_numbers=(...))` |
| P10 | `SamplingSimulator` 已弃用 | 用 `PassiveSimulator` |
| P11 | `GaussianState.density_matrix` 的大小由 `Config(cutoff=N)` 控制，**`measurement_cutoff` 无效** | 设 `cutoff` |
| P12 | `Result.branches` 是 **list**（元素为 `Branch`：`.state/.outcome/.frequency`），不是 dict | 按 list 遍历 |
| P13 | homodyne 末端测量在 `PureFockSimulator` 上不支持 `shots=None` | 必须给 `shots` |

## 7. 对 cvsim 的行动含义

1. **piquasso 值得接入，但只作为"非高斯 + 条件化、无通道"的 oracle**（§5 的 ✅ 行）。这正是 `tests/_golden/sf_fock_golden.npz` 的空洞。
2. **"通道 + 条件化"这一格必须走别的路**：要么等上游修复，要么退回 cvsim 自己的闭式锚点（loss 通道有精确闭式：`ρ₀₀=1−T`、`ρ₁₁=T`、相干/压缩在 loss 下均值缩放 `√T`）。
3. 接入方式必须是 **R1 离线冻结**：一次性 venv 跑出 golden → 存 npz → 测试只读文件、零 piquasso import。**不要**做活依赖（`tests/test_walrus.py` 的 12 个 skip 就是活依赖腐烂的现成教训）。
4. 生成脚本**禁止**对 cvsim 自检（`tools/gen_sf_golden.py` 里 `max|SF−cvsim| < 1e-8` 才写盘是它的缺陷：只能锁，不能发现）。新脚本原样写参考实现的输出。
5. 任何外部 golden 落地前，先跑 `tools/qualify_piquasso_oracle.py` 复验——上游升级可能引入新的物理 bug（piquasso 历史上 `Kerr` 多模错两次、`GaussianState.fidelity` 多模错过）。

## 8. 复现命令

```powershell
# 一次性 venv（不要装进项目 .venv）
uv venv $env:TEMP\pq-probe --python 3.13
uv pip install --python $env:TEMP\pq-probe\Scripts\python.exe piquasso

# 资格认证
& $env:TEMP\pq-probe\Scripts\python.exe tools\qualify_piquasso_oracle.py
# 期望：SUMMARY: 43 PASS / 0 FAIL
```

## 9. 相关

- `tests/_golden/sf_fock_golden.npz` + `tests/test_sf_golden_f6.py` —— 现有唯一的外部实现 oracle（SF 0.23.0，Fock 单引擎，8 例）
- `tools/gen_sf_golden.py` —— 离线冻结的既有先例
- `docs/sf-roundtrip-fock.md` —— SF 侧的约定映射表（本文档是它的 piquasso 对应物）
- `docs/adr/0005-bosonic-production-vision.md` —— 记录过"R3：等外部 golden，SF 无成熟 Bosonic GKP 表示，等不到"
- `tests/test_b4_bosonic_reconciliation.py` —— 分层对账 Layer 1/2 的现状
