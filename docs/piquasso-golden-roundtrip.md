# piquasso golden round-trip（Fock 复合 / 3+ 模 / 条件化）

> 对应 `docs/sf-roundtrip-fock.md`（Strawberry Fields 侧）。本文档记录 piquasso 侧的约定映射，供 `tests/test_piquasso_golden.py` 与 `tools/gen_piquasso_golden.py` 使用。

## 1. 为什么有这一套

`tests/_golden/sf_fock_golden.npz`（SF 0.23.0）是仓库里唯一的外部实现 oracle，但它覆盖的是**单门/双门门演化**：8 例、≤2 模、**无 3+ 模电路、无测量、无条件化、无通道**——恰好是 cvsim 本来就有闭式的那部分。

piquasso golden 专门补它盖不到的三格：

| 覆盖 | SF golden | piquasso golden |
|---|---|---|
| 1–2 模门演化 | ✅ 8 例 | —（不重复） |
| **3 模非高斯链** | ❌ | ✅ `chain3_ket`（cutoff 40） |
| **4 模非高斯链** | ❌ | ✅ `chain4_ket`（cutoff 32） |
| **3 模 PNR 联合分布** | ❌ | ✅ `chain3_pnr_joint`（cutoff 28） |
| **PNR 后选择 / 条件化** | ❌ | ✅ `chain3_post_k{0,1,2}_joint` |

**先资格认证，再当 oracle**：`tools/qualify_piquasso_oracle.py` 用 cvsim 自己已信的 43 条闭式锤过 piquasso（全过，≤1e-12，含精确条件化），它才有资格在这里当参考。未经认证的外部库当 oracle = 制造假信心。

## 2. 版本锁

| 项 | 值 |
|---|---|
| piquasso | **8.0.1** |
| numpy | 2.5.3（生成时） |
| hbar | 1（cvsim 约定） |
| 生成日期 | 见 npz metadata |

piquasso **不是**项目依赖（最小依赖是 ADR 级红线）。它只活在一次性的生成 venv 里；测试期只读 npz。

## 3. 约定映射表（全部实测钉死）

| # | 项 | 约定 |
|---|---|---|
| R1 | `Config.hbar` | **默认 2.0**；必须显式 `hbar=1`。此时 `xxpp_covariance_matrix == cvsim 2V`、`xxpp_mean_vector == cvsim rbar`，零缩放因子 |
| R2 | **beamsplitter** | cvsim `beamsplitter(θ, φ)` == piquasso `Beamsplitter(-θ, -φ)`（实测 1.1e-16） |
| R3 | squeeze / displace / kerr / two_mode_squeeze | 同号，无需翻转 |
| R4 | 张量轴序 | **完全一致**（mode 0 在前）；`get_tensor_representation()` 给稠密 `(cutoff,)*m` |
| R5 | **cutoff 语义** | **最大的坑**。piquasso `Config(cutoff=N)` 是**总光子数**截断（`sum_i n_i < N`，`state_vector` 长度 = `C(N+m-1, m)`）；cvsim 是**每模**截断（稠密 `(N,)*m`）。两者只在 piquasso 的单纯形上重合，所以 `N` 越大越吻合 |
| R6 | 归一化 | piquasso **不**对截断后态重归一（norm 可 < 1）；cvsim **会**（norm 恒 = 1）。本套 golden 里后选择态已除以选择概率 |
| R7 | 真空初始化 | **Fock 模拟器不隐式初始化真空**——`Squeezing`/`Displacement` 单独跑得全零态（norm=0）。必须显式准备 |
| R8 | `Vacuum()` + `NumberState()` | **叠加相加**（norm 变 2），**不是替换**。要 `NumberState` 就单独用 |
| R9 | 测量条件化 | `PostSelectPhotons(photon_counts=(k,))` **删掉被后选择的模**：nmode → nmode−1。返回未归一态，选择概率 = trace |
| R10 | `Attenuator(theta)` | 透射率是 **T = cos²θ** |
| R11 | `GaussianSimulator` 多测量样本 | 是 `(值, 权重)` **成对**的；无权重 `.var()` 无意义 |
| R12 | 占据数序 | 1.0.0 起为**反字典序**；用 `fock_probabilities_map`，别用扁平索引 |
| R13 | `pq.StateVector` / `SamplingSimulator` | 均已弃用 → `NumberState` / `PassiveSimulator` |
| R14 | `GaussianState` 的 `fock_probabilities` 长度 | 由 `Config(cutoff=N)` 控制，**`measurement_cutoff` 无效** |

## 4. 生成方式（R1 离线冻结）

```powershell
# 一次性 venv（不要装进项目 .venv）
uv venv $env:TEMP\pq-gen --python 3.13
uv pip install --python $env:TEMP\pq-gen\Scripts\python.exe piquasso

# 生成 golden（写盘 + 打印 cvsim 对比诊断）
& $env:TEMP\pq-gen\Scripts\python.exe tools\gen_piquasso_golden.py
# 期望：saved ... (0.24 MB)，每个 case 的 max|diff| 见下表
```

**生成脚本不对 cvsim 自检**（与 `tools/gen_sf_golden.py` 的关键差别）。后者算 `max|SF−cvsim| < 1e-8` 才写盘，只能**锁住**已有的一致性，**发现不了**分歧。这里参考实现的输出原样写盘，cvsim 对比只打印、不设门。分歧必须表现为**红的测试**，而不是"拒绝生成"。

## 5. 冻结的 case 与收敛残差

残差主因是 R5 的 cutoff 语义错配（不是任何一边算错），随 cutoff 增大而收敛。

| case | cutoff | 形状 | 残差 | 余量 |
|---|---|---|---|---|
| `chain3_ket` | 40 | (40,40,40) complex | 4.3e-13 | ~23000× |
| `chain4_ket` | 32 | (32,32,32,32) complex | 5.3e-12 | ~1900× |
| `chain3_pnr_joint` | 28 | (28,28,28) float | 2.5e-14 | ~400000× |
| `chain3_post_k0_joint` | 28 | (28,28) float | 2.3e-16 | — |
| `chain3_post_k1_joint` | 28 | (28,28) float | 4.9e-14 | — |
| `chain3_post_k2_joint` | 28 | (28,28) float | 7.6e-13 | ~13000× |

测试判据 `atol=1e-8`（与 SF golden 同标准）。**每个 case 余量 ≥ 1000×**——残差是确定性截断偏差、不是噪声，所以不会 flaky。

`savez_compressed` 把 8.41 MB 压到 **0.26 MB**——稠密张量在 piquasso 的总光子单纯形外几乎全零。

## 6. 测试非空性验证（变异测试）

只跑"通过"不能证明测试有效。已实测：

| 变异 | 检出 |
|---|---|
| golden 数据扰动 +1e-6（=100×atol） | ✅ 全部 6 个张量 |
| `r=0.30` → `0.31` | ✅ 4.5e-3 |
| BS `θ=0.50` → `0.51` | ✅ 2.1e-3 |
| **BS 符号翻转 `θ=0.50` → `−0.50`** | ✅ 2.5e-1 |
| 条件化 `k=0` → `n=3` | ✅ 9.6e-1 |

BS 符号翻转被检出尤其重要——那正是 R2 最易犯的错。

## 7. 已知能力边界（不在本套 golden 里）

`PureFockSimulator` 在**通道（`Attenuator`）之后接任何后续指令**时崩溃：

```
AttributeError: 'FockState' object has no attribute 'state_vector'
  at piquasso/_simulators/fock/pure/simulation_steps/utils.py:63
```

`FockSimulator`（密度矩阵后端）扛得住通道，但**完全不支持 homodyne**。两个后端的算力互斥，`pq.simulate()` 自动选择也救不了。所以：

- **非高斯 + 条件化（无通道）** → 本套 golden 覆盖 ✅
- **通道 + 条件化** → piquasso 目前无解 ❌，需走 cvsim 自己的闭式锚点（loss 通道有精确解：`ρ₀₀=1−T`、`ρ₁₁=T`、均值缩 `√T`）

详见 `docs/piquasso-oracle-qualification.md` §4–5。

## 8. 相关

- `tools/qualify_piquasso_oracle.py` — 资格认证脚本（43 判据）
- `docs/piquasso-oracle-qualification.md` — 资格认证结论 + 能力边界
- `tools/gen_piquasso_golden.py` — 本套 golden 的生成脚本
- `tests/test_piquasso_golden.py` — 消费测试（零 piquasso 依赖）
- `docs/sf-roundtrip-fock.md` / `tests/test_sf_golden_f6.py` — SF 侧同类（1–2 模门演化）
- `.github/workflows/ci.yml` — CI 不装 piquasso；本套测试只读 npz，无额外依赖
