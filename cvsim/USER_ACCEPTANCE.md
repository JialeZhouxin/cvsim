# 最终用户验收（cvsim）

> 工程验收文档（可指 API）。理论笔记仍纯物理，不绑本包。  
> 能力边界：MVP + B1 门 + B2 Homodyne 边缘矩。  
> 版本锚点：pytest 约 **25** passed（随切片更新本数）。

---

## 项目目标

### 两层

| 层 | 是什么 | 成功 |
|----|--------|------|
| 理论笔记 | CV 三表示纯物理自学 | 人能按根 README 四步想通：挤 / det·⟨n⟩ / Fock 扫 / 小 cat |
| `cvsim` | 笔记落地的最小三表示模拟器 | 无量子库；numpy+scipy；同一约定下可跑、可测 |

### 产品一句话

**读完笔记 → 跑 `cvsim` → 同一套数：** ħ=1、xxpp、真空 `V=I/2`；Gaussian 挤+分束+Homodyne 边缘；Fock cutoff 逼近；Bosonic cat 权重与高斯门。

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
| Homodyne | `x_φ = x cosφ + p sinφ`；`Var = uᵀ V u`（中心矩） |

---

## 环境

```bash
uv venv
.venv\Scripts\activate   # Windows
uv pip install numpy scipy pytest
```

---

## 一键用户验收（U1–U5）

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

### U3 · 有意义高斯电路（B1+B2）

| | |
|--|--|
| 笔记 | 02 门表；B1/B2 |
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

- S₂ 双模挤压  
- Homodyne 条件态更新 / 采样  
- 光子损失通道  
- Fock 多模 BS / Kerr  
- Wigner 网格必选 / GKP  
- Circuit DSL；PNRD / Hafnian / Torontonian 生产路径  

新切片落地后：在本文件 **加 Ux**、改一键 demo、更新 pytest 计数；**少改**「项目目标」段。

---

## 更新约定

1. 物理约定改动必须同步 `.trellis/spec/backend/quality-guidelines.md` 与本文件。  
2. 用户场景优先复用既有 `tests/` 数字，避免第二套容差。  
3. 理论根目录 `*.md` 不写 `cvsim` API。
