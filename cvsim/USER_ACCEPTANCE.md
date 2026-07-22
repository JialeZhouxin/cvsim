# 最终用户验收（cvsim）

> 工程验收文档（可指 API）。理论笔记仍纯物理，不绑本包。  
> 能力边界：三表示独立闭环 + G/B condition·sample·loss + F 1–2 模 BS/Kerr/PNRD + F 1 模 loss→ρ/门 + **Fock Wigner** + B 矩/`gkp0`/Wigner + sample_and_condition。  
> 版本锚点：pytest **105** passed（切片后请改本数）。

---

## 项目目标

### 两层

| 层 | 是什么 | 成功 |
|----|--------|------|
| 理论笔记 | CV 三表示纯物理自学 | 人能按根 README 四步想通：挤 / det·⟨n⟩ / Fock 扫 / 小 cat |
| `cvsim` | 笔记落地的最小三表示模拟器 | 无量子库；numpy+scipy；同一约定下可跑、可测 |

### 产品一句话

**读完笔记 → 跑 `cvsim` → 同一套数：** ħ=1、xxpp、真空 `V=I/2`。

| 表示 | 当前闭环（摘要） |
|------|------------------|
| **Gaussian** | 门 D/R/S/BS/S₂ → `loss(T, nbar=0)` → 边缘 / **sample** / 条件 Homodyne → 矩 |
| **Fock** | 1–2 模；D/R/S/Kerr/BS/**S₂** → PNRD / norm / ⟨n⟩；**1 模 Homodyne mean/var/sample**；**1 模 `loss→FockDensity`**；**ρ 上 D/R/S**；**单模 Wigner** |
| **Bosonic** | cat / `gkp0` → 门 → ∑w 加权矩 → `loss(T, nbar=0)` → **sample** / **condition（复仿射）** / **sample_and_condition** |

### 不是目标

- 生产级 GBS / Hafnian 大规模
- Circuit DSL
- 替代 Strawberry Fields / DeepQuantum
- 在理论 `*.md` 里塞 API

---

## 约定（不可静默改）

| 项 | 值 |
|----|-----|
| ħ | 1 |
| 正交序 | xxpp：`(x₁…xₘ, p₁…pₘ)` |
| 真空 | `V=I/2`，`r̄=0` |
| 纯单模高斯 | `det V = 1/4` |
| 挤态平均光子 | `⟨n⟩ = sinh² r` |
| 位移 | `d_x=√2 Re α`，`d_p=√2 Im α` |
| Homodyne | `x_φ = x cosφ + p sinφ`；高斯边缘 `Var = uᵀ V u`（中心矩） |
| 损失 | G/B：`X=√T`，`Y=(1-T)(n̄+1/2)I`（`n̄=0` 纯损耗）；F：1 模 Kraus，`T∈[0,1]` |
| GKP `gkp0` | 对角 x 齿梳；可选 `cross="nn"`；间距 `√(2π)` |

细节合同：`.trellis/spec/backend/quality-guidelines.md`。

---

## 环境

```bash
uv venv
.venv\Scripts\activate   # Windows
uv pip install numpy scipy pytest
```

---

## 一键用户验收（U1–U5 + U7–U9）

```bash
python -m cvsim.demos.user_acceptance
```

- 跑完 **全部** 场景后汇总 PASS/FAIL  
- 任一 FAIL → exit code **1**；全绿 → **0**

---

## 场景

### U1 · 真空与约定

| | |
|--|--|
| 笔记 | 术语表、00、02 §真空 |
| 操作 | `GaussianState.vacuum(1)` |
| 期望 | `r̄≈0`；`V≈0.5 I`；`det V ≈ 1/4` |
| 容差 | `1e-12` 量级 |

### U2 · Gaussian 挤压主线

| | |
|--|--|
| 笔记 | 02；根 README 闭环 1–2 |
| 操作 | 真空 → `squeeze(r=0.8)` |
| 期望 | `det V ≈ 1/4`；`|⟨n⟩−sinh²r|` 小；`var(x)=½e^{-2r}`，`var(p)=½e^{2r}` |
| 容差 | `1e-10` |

### U3 · 有意义高斯电路（门 + 边缘 Homodyne）

| | |
|--|--|
| 笔记 | 02 门表 |
| 操作 | `D(α)`；`S→BS(π/4)`；挤后 `phase` |
| 期望 | `⟨n⟩≈|α|²`；Homodyne mean 跟 √2 约定；BS 后总 `⟨n⟩=sinh²r`，`det V≈(1/4)²`；phase 后 `var` 仍 = `uᵀVu` 且相对纯挤变化 |
| 容差 | `1e-10`～`1e-12` |

### U4 · Fock 截断

| | |
|--|--|
| 笔记 | 01、04；根 README 闭环 3 |
| 操作 | 同 `r=0.5` 扫 cutoff；高 N 演化再投到低 N |
| 期望 | 大 cutoff 时 `⟨n⟩` 逼近 `sinh²r`；误差随 N 降；投影范数亏损 > 0 |
| 容差 | 与 m2 一致（大 N `err<1e-3`；deficit `>1e-4`） |

### U5 · Bosonic cat

| | |
|--|--|
| 笔记 | 03、04；根 README 闭环 4 |
| 操作 | `even_cat(0.8)`；`phase` |
| 期望 | 4 组件；`∑w≈1`；phase 后 `∑w` 仍 1，对角峰旋转 |
| 容差 | `1e-12` |

### U7 · 扩展能力冒烟（G/F/B 后续切片）

| 子项 | 操作 | 期望 |
|------|------|------|
| G loss | 相干 `D(α)` → `loss(T)` | `⟨n⟩≈T\|α\|²` |
| G condition | 真空 → `homodyne_condition(…, outcome)` | 测向 var→0；`⟨x⟩→outcome` |
| F BS | `\|10⟩` → `BS(π/4)` | `\|c₁₀\|²≈\|c₀₁\|²≈½` |
| B gkp0 | `gkp0(0.1, N=3)` | `K=7`，`∑w≈1`，Δx=`√(2π)` |
| B loss | `even_cat` → `loss(0)` | `⟨n⟩≈0`，`∑w=1` |

### U8 · 队列 ①②③ 冒烟（B condition / sample / Fock loss）

| 子项 | 操作 | 期望 |
|------|------|------|
| B condition | `even_cat` → `homodyne_condition` +outcome | K=4；`∑w≈1`；+diag `|w|` > −diag |
| G sample | 真空 N=2000，固定 seed | `|mean|<0.08`；`|var−0.5|<0.08` |
| B sample | `from_gaussian` 同 seed ≡ G | 单次差 `<1e-12` |
| F loss | `\|1⟩` → `loss(T)` | `ρ₀₀≈1−T`，`ρ₁₁≈T`；`Tr≈1` |

### U9 · P0 gap-fill 冒烟（Fock Wigner / ρ 门 / sample_and_condition）

| 子项 | 操作 | 期望 |
|------|------|------|
| F Wigner | 真空 / \|1⟩ 中心 | \(W_{\mathrm{vac}}(0,0)\approx1/\pi\)；\|1⟩ 中心负 |
| ρ 门 | \|1⟩→loss→displace | Tr≈1 |
| sample+cond | G 真空 | 测向 var→0；⟨x⟩→outcome |

### U6 · 机器门禁（文档命令，不在一键 demo 内强制）

```bash
python -m pytest tests -q
python -m cvsim.demos.m1_gaussian_squeeze
python -m cvsim.demos.m2_fock_cutoff_scan
python -m cvsim.demos.m3_cat_weights
python -m cvsim.demos.user_acceptance
```

期望：pytest 全绿；各 demo 打印 OK / 全 PASS。

---

## 未做（当前不验收为绿）

- Fock **2 模 loss** / m≥3 / Fock Homodyne **condition**  
- **完整纯态 GKP**（full-pair cross / `|1⟩` / 二维格点）  
- 多模 Wigner / GUI  
- Circuit DSL；PNRD 大规模；Hafnian / Torontonian 生产路径  

已落地（见 U7–U9 + P1 A/B）：G/B Homodyne sample + **sample_and_condition**；B condition；Fock 1 模 loss→ρ + **ρ 门** + **S₂** + **Homodyne mean/var/sample**；**Wigner G+B+F**；GKP nn cross；G/B **`loss(..., nbar)`**。

新切片落地后：在本文件 **加 Ux**、改一键 demo、更新 pytest 计数；**少改**「项目目标」段。

---

## 更新约定

1. 物理约定改动必须同步 `.trellis/spec/backend/quality-guidelines.md` 与本文件。  
2. 用户场景优先复用既有 `tests/` 数字，避免第二套容差。  
3. 理论根目录 `*.md` 不写 `cvsim` API。
