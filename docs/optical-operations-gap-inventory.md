# cvsim 光学操作缺口盘点（三表示对比）

**日期**: 2026-09-02 · **作者**: 会话探索(pi)
**用途**: 全景盘点 cvsim 三表示（gaussian / fock / bosonic）已模拟的光学操作，对照现实量子光学全集找出未引入的缺口，为能力完备性 roadmap 提供参考。
**范围**: 仅盘点**单模/双模连续变量**光学操作；多模生产级、协议库、AD、张量网络不在内（vision 各表示 §1.3）。

---

## 0. 约定

- 三表示：**gaussian**（高斯态，symplectic 映射，快）、**fock**（截断振幅，expm 矩阵，精确慢）、**bosonic**（分量/Wigner 表示，非高斯态以复高斯分量叠加承载）。
- `✅`=已实现；`🟡`=部分/近似；`❌`=未实现。
- 跨表示差异本质：gaussian 仅闭环高斯流形；fock 可承载任意态但受 cutoff 截断；bosonic 以分量叠加承载非高斯态，但受表示限制。

### `phi` 约定分歧（fock vs gaussian/bosonic）—— **landmine**

fock `phi` 是**压缩幅角**：`ξ = r·e^{iφ}`，压缩算符 `U = exp(½(conj(ξ)·a² − ξ·a†²))`，
`FockState.squeezed` 的 `c_{2n} ∝ (e^{iφ}·tanh r)^n`。
gaussian/bosonic `phi` 是**协方差旋转角**（`gaussian.gates.squeeze` = `R(φ)·S(r)·R(−φ)`）。

→ **两者差 2 倍**：`FockState.squeezed(φ=0.8)` 与 gaussian `φ=0.4` 同物理态（maxdiff 6.7e-16）。
已由 `tests/test_fock_squeeze_phi.py` 哨兵锁死；统一 = 破坏性变更（改已提交 gold `tests/test_b9_bosonic_pnr.py`），独立任务。

### 已修的跨表示缺陷（留档，防回退）

| 缺陷 | 位置 | 修复 | 任务 |
|---|---|---|---|
| `cx` 生成元符号 `+i`（= 高斯的逆门） | `cvsim/fock/gates.py` `_cx_U` | 改 `−i`（CZ `+i` / CX `−i` 本应相反） | `09-21-fock-cx-sign-mismatch` |
| `mach_zehnder` 相位加在 mode2 + 首 BS 多带 φ | `cvsim/fock/{circuit,gates}.py` 两份 | 改 canonical `BS(π/4,0)·(P(φ)⊗I)·BS(θ,0)` | `09-22-fock-mz-divergence` |
| **fock Wigner 核 `α`/`ᾱ` 两分支对调**（`⟨p̂⟩ ≠ 0` 时热图 p 轴镜像） | `cvsim/wigner.py` `_wigner_kernel_nm` + `_wigner_grid_fock` | 两处对调 | `09-22-fock-wigner-cx-bs` |
| `cx` 忽略 `mode1`/`mode2`（CX 不对称） | `cvsim/fock/gates.py` | SWAP 共轭 | `09-22-fock-wigner-cx-bs` |
| `beamsplitter` 无 mode 参数（BS 不对称） | `cvsim/fock/gates.py` | 尾加 `mode1=0, mode2=1` + SWAP 共轭 | `09-22-fock-wigner-cx-bs` |

共同病因：**跨表示/跨分支断言对被测参数不敏感** —— 详见 `.trellis/spec/cvsim/index.md` 的「对称性陷阱」条。

---

## 1. 高斯门（三表示基本都有）

| 门 | gaussian | fock | bosonic | 备注 |
|---|---|---|---|---|
| `squeeze(r[, phi])` | ✅ | ✅ | ✅ | 三表示均带 `phi`（fock 09-14 补齐；**约定分歧**：fock `phi` 是压缩幅角 `ξ=r·e^{iφ}`，gaussian/bosonic 是协方差旋转角 —— 差 2 倍，见下） |
| `displace(alpha)` | ✅ | ✅ | ✅ | 纯相空间平移 |
| `phase(theta)` | ✅ | ✅ | ✅ | |
| `beamsplitter(theta, phi)` | ✅ | ✅ | ✅ | 三表示均带 mode 参数。**曾缺失**：fock 原签名 `(state, theta, phi)` 无模式参数，`09-22-fock-wigner-cx-bs` 尾加 `mode1=0, mode2=1`（kw-only，向后兼容）。BS **不是模式对称的**（实测 `(0,1) ≠ (1,0)`），反序走 SWAP 共轭 |
| `two_mode_squeeze(r)` | ✅ | ✅ | ✅ | fock 忽略 mode 序但该门对模式交换**对称**，无害 |
| `cz(weight)` | ✅ | ✅ | ✅ | CV 受控 Z `exp(+i·w·x̂₁x̂₂)`；对模式交换对称，fock 忽略 mode 序无害。**曾默认值分歧**：fock 的 `weight` 默认 `1.0`（其余所有门、所有包都是恒等 `0.0`），省略 weight 时 fock 建出纠缠门而 gaussian/bosonic 建出恒等 —— 同一段残缺电路在三后端含义不同。`09-22-fock-cz-cx-weight-default` 已对齐为 `0.0` |
| `cx(weight)` | ✅ | ✅ | ✅ | CV 受控 X `exp(−i·w·x̂₁p̂₂)`。**曾符号分歧**：fock `_cx_U` 误用 `+i`（= 高斯的逆门），`09-21-fock-cx-sign-mismatch` 已对齐；`cz = exp(+i·w·x₁x₂)` 是 `+i`，两者符号本应相反。**曾忽略 mode 序**：`09-22-fock-wigner-cx-bs` 已修（CX **不对称**，反序走 SWAP 共轭）。注意 Lab 走 `FockCircuit`（本来就对），只有 `cvsim.fock.gates.cx` 这条独立实现曾错。**曾默认值分歧**：同 `cz`，fock `weight` 默认 `1.0` → 已对齐 `0.0`（`09-22-fock-cz-cx-weight-default`） |
| `fourier()` | ✅ | ✅ | ✅ | = phase(π/2) |
| `mach_zehnder(m1, m2, theta, phi)` | ✅ | ✅ | ✅ | canonical `BS(π/4,0)·(P(φ)⊗I)·BS(θ,0)`（= `S_mach_zehnder`，**相位在 mode1**）。**曾分歧**：fock 相位加在 mode2 且首 BS 多带 φ，`09-22-fock-mz-divergence` 已对齐。**曾参数序分歧**：fock `gates.mach_zehnder` 原为 `(state, theta, phi, mode1, mode2)` —— 五个参数名相同、中间三个含义不同，位置调用会静默把 modes 和 angles 对调（不报错，只是换了个门），`09-22-fock-mz-arg-order` 已对齐为 `(state, mode1, mode2, theta, phi)`（vision `docs/vision-gaussian-simulator.md:333` 冻结序）。**Lab op 名陷阱**：gaussian 的 `mz` 是**另一个门**（`BS(θ)→P(φ)→BS(θ)`，`cvsim/gaussian/ir.py::_expand_mz`），与 `mach_zehnder` 不同；fock/bosonic 只有 `mach_zehnder`。跨后端对拍不能用 `mz` vs `mach_zehnder` |
| `interferometer(U)` | ✅ | ✅(m≤2) | ✅ | fock 仅 2×2 |

**差异**：gaussian/bosonic 门走 symplectic 映射（O(m²)），fock 走 `expm` 矩阵（O(N²ᵐ)，慢但精确）。fock 的 `interferometer` 仅支持 m≤2（稠密锚）。

---

## 2. 非高斯门（核心缺口，仅实现了 kerr）

| 操作 | 物理 | gaussian | fock | bosonic | 备注 |
|---|---|---|---|---|---|
| **kerr 单模** `e^{iχ n²}` | 克尔效应，`|n⟩→e^{iχn²}|n⟩` | ❌(非高斯不闭) | ✅ | ✅(分量展开, 2026-09-02) | 唯一已实现的非高斯门 |
| **Cross-Kerr 双模** `e^{iχ n₁n₂}` | 克尔交叉项，纠缠/逻辑门资源 | ❌ | ❌ | ❌ | 与单模 kerr 同族但双模 |
| **三波混频 η** `e^{iη(a²b†+h.c.)}` | 非简并三波，非高斯纠缠 | ❌ | ❌ | ❌ | |
| **四波混频 / SPDC 哈密顿量谱** | 参量下转换的非高斯修正 | ❌ | ❌ | ❌ | |
| **Echo / Generalized Kerr** `e^{iχ n² + iβ n}` | Kerr+线性相移组合 | ❌ | ❌ | ❌ | |
| **广义多项式相位门** `e^{i f(n)}` | 任意 Fock 相位 | ❌ | ❌ | ❌ | 非高斯门全集 |

---

## 3. 测量（关键缺口：PNR 光子数分辨）

| 测量 | gaussian | fock | bosonic | 备注 |
|---|---|---|---|---|
| `homodyne` (零差) | ✅ | ✅ | ✅ | fock 单模为主 |
| `heterodyne` (外差/Husimi Q) | ✅ | ✅ | ✅ | bosonic 精确 2D Q 面 (ADR-0007) |
| `threshold` (on/off 点击) | ✅ | ✅ | ✅ | outcome-only，无态更新 |
| **`pnr` 光子数分辨** | ❌ | ✅ | 🟡 | Bosonic B9 已支持单模边际 `pnr_probs`/`pnr_sample`；`pnr_condition` 与联合多模 PNR 仍未实现 |
| **general-dyne** (8 端口连续族) | ❌ | ❌ | ❌ | 介乎 homodyne/heterodyne 的广义测量 |
| **探测态 / 层析重建** | ❌ | ❌ | ❌ | 条件态重构 + 反馈 |

---

## 4. 通道

| 通道 | gaussian | fock | bosonic | 备注 |
|---|---|---|---|---|
| `loss(T[, nbar])` | ✅ | ✅ | ✅ | 纯损耗/热损耗 |
| `amplifier(G[, nbar])` | ✅ | ✅ | ✅ | 相不敏感放大 |
| `phase_noise(sigma)` | ✅ | ✅ | ✅ | 高斯随机旋转平均（精确退相位的近似） |
| `apply_kraus` (通用 Kraus) | ❌ | ✅ | ❌ | fock 独有；gaussian/bosonic 只能就单一具体通道 |
| **纯退相干 (exact dephasing)** | 🟡 | 🟡 | 🟡 | 现为高斯近似 `X=e^{−σ²/2}I, Y=(1−e^{−σ²})½I` |
| **通用 CPTP / 任意 (X,Y) 高斯通道** | 🟡 | 🟡 | 🟡 | 只硬编码 loss/amp/phase_noise，无通用参数化（fock 靠 apply_kraus 部分覆盖） |
| **非马尔可夫损耗 / 振幅阻尼** | ❌ | ❌ | ❌ | |

---

## 5. 态工厂

| 态工厂 | gaussian | fock | bosonic | 备注 |
|---|---|---|---|---|
| `vacuum` | ✅ | ✅ | ✅ | |
| `coherent(alpha)` | ✅ | ✅ | ✅ | |
| `squeezed(r, phi)` | ✅ | ✅ | ❌ | **bosonic 缺失**（仅能 from_gaussian 包装） |
| `displaced_squeezed(alpha, r)` | ✅ | ❌ | ❌ | |
| `tmsv(r)` (双模压缩真空) | ✅ | ❌ | ❌ | gaussian 独有 |
| `cat` (偶/奇猫) | ❌ | ✅ | ✅(even/odd_cat) | |
| `gkp0/gkp1` | ❌ | ✅ | ✅ | bosonic 手工分量 |
| `fock(n)` / Fock 数态 | ❌ | ✅ | ❌ | **bosonic 无法表示纯 Fock 态**（表示限制） |
| **热态 / 有限温度** | ✅ | ❌ | ❌ | gaussian 有热态；需 thermal factory |
| **纠缠态（双模 cat、编码纠缠）** | ❌ | ❌ | ❌ | |

---

## 6. 按价值排序的动手缺口

### Top-4（值得优先）

1. **Bosonic PNR 完整化** — ✅ 2026-09-08 基本落地（ADR-0012，任务 `09-08-pnr-condition-state-bridge`）：概率面 B9/B10 已交付；后验走根层态桥 `cvsim/bridge.py`（`bosonic_to_fock` + `pnr_condition_bosonic` / `pnr_sample_and_condition_bosonic`，后验表示 = fock，两步桥）。剩余缺口：m≥3 整态桥与 2 模混合分量（ADR-0012 future work）；电路内联合后验仍延期。
2. **Cross-Kerr 双模门** `e^{iχ n₁n₂}` — 与单模 kerr 同族但双模，是量子逻辑门、纠缠生成、非高斯纠错方案的核心资源；补上可扩展 bosonic 的非高斯能力覆盖。
3. **bosonic `squeezed` 态工厂** — 一致性缺口：gaussian/fock 都有，bosonic 缺失，补上可与 `from_gaussian` 对账（K=1 对齐测试）。
4. **general-dyne 广义测量** — 连续变量测量的完整族（8 端口干涉仪），目前只覆盖 homodyne/heterodyne 两个端点，缺中间连续族。

### 次要 / 探索性

- 三波/四波混频、SPDC 哈密顿量谱、polynomial phase 门（非高斯门全集）
- 双模 TMSV 工厂、纠缠态工厂
- 通用 CPTP 高斯通道参数化、精确退相干、非马尔可夫损耗
- 热态工厂、探测态层析

---

## 7. 表示层的本质限制（非"可补"而是"原理不可"）

- **bosonic 无法表示纯 Fock 数态**：Fock 态非高斯且非有限分量，bosonic 用复高斯分量叠加承载非高斯态，纯 `|n⟩` 无有限分量表示。这与 vision §1.3 的表示边界一致。
- **gaussian 无法表示任何非高斯态**：高斯流形闭环，cat/GKP/kerr 都超出。这是 gaussian 表示的根本限制。
- **从真空出位置梳 GKP 非目标**：需 stabilizer 测量 + 位移反馈（高斯主导），单靠 kerr 不行（见 `docs/gkp-preparation-from-vacuum.md`）。

---

## 参考资料

- `docs/vision-bosonic-simulator.md` §1.3 / §6 — bosonic 能力与非目标
- `docs/vision-fock-simulator.md` — fock 能力与非目标
- `docs/vision-gaussian-simulator.md` — gaussian 能力与非目标
- `.trellis/spec/cvsim/*.md` — 各表示生产面契约
- `docs/phase0-kerr-component-expansion.md` — bosonic kerr 分量展开可行性结论
