# cvsim 光学操作缺口盘点（三表示对比）

**日期**: 2026-09-02 · **作者**: 会话探索(pi)
**用途**: 全景盘点 cvsim 三表示（gaussian / fock / bosonic）已模拟的光学操作，对照现实量子光学全集找出未引入的缺口，为能力完备性 roadmap 提供参考。
**范围**: 仅盘点**单模/双模连续变量**光学操作；多模生产级、协议库、AD、张量网络不在内（vision 各表示 §1.3）。

---

## 0. 约定

- 三表示：**gaussian**（高斯态，symplectic 映射，快）、**fock**（截断振幅，expm 矩阵，精确慢）、**bosonic**（分量/Wigner 表示，非高斯态以复高斯分量叠加承载）。
- `✅`=已实现；`🟡`=部分/近似；`❌`=未实现。
- 跨表示差异本质：gaussian 仅闭环高斯流形；fock 可承载任意态但受 cutoff 截断；bosonic 以分量叠加承载非高斯态，但受表示限制。

---

## 1. 高斯门（三表示基本都有）

| 门 | gaussian | fock | bosonic | 备注 |
|---|---|---|---|---|
| `squeeze(r[, phi])` | ✅ | ✅ | ✅ | gaussian/bosonic 的 squeeze 带 `phi`；fock 仅实 r |
| `displace(alpha)` | ✅ | ✅ | ✅ | 纯相空间平移 |
| `phase(theta)` | ✅ | ✅ | ✅ | |
| `beamsplitter(theta, phi)` | ✅ | ✅ | ✅ | |
| `two_mode_squeeze(r)` | ✅ | ✅ | ✅ | |
| `cz(weight)` | ✅ | ✅ | ✅ | CV 受控 Z |
| `cx(weight)` | ✅ | ✅ | ✅ | CV 受控 X |
| `fourier()` | ✅ | ✅ | ✅ | = phase(π/2) |
| `mach_zehnder(theta, phi)` | ✅ | ✅ | ✅ | |
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

1. **Bosonic PNR 完整化** — B9 已补单模边际概率/采样；剩余缺口是 `pnr_condition` 与联合多模 PNR。PNR 是门控、掺 Er 纠错、HOM 层析基础；Fock 端继续作为 gold 锚。后续需先决定 PNR 后验表示，再扩展 Bosonic（**AD 模块边界：Fock 可精确，Bosonic 单模边际走生成函数**）。
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
