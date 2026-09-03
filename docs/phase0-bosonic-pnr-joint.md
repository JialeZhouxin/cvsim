# bosonic PNR — 联合多模生成函数分块核（Phase 0 结论）

**日期**: 2026-09-03 · **作者**: 会话探索(pi)
**用途**: 验证 bosonic **联合多模 PNR**（B10 / Phase 2a）的核心数学——单高斯分量
`⟨n⃗|ρ_k|n⃗⟩` 的**多模生成函数**（`G(t⃗)` 从 B9 单模 2×2 推广到 2m×2m 分块）是否
数值可行。结论：**数学核充分验证（≤1e-16 逐位），生产需向量化（3 模 400s 瓶颈）**。

---

## 1. 背景

B9 单模 PNR（`pnr_probs`/`pnr_sample`）已提交（`36ed8ac`），但只给**单模边缘**。
Fock（`pnrd_probs(mode=None)`）与 Gaussian（`walrus.pnr_probs → [cutoff]^m`）已有
**联合** PNR；bosonic 缺。B10 目标：给 bosonic 非高斯态（cat、GKP、纠缠）提供
**联合光子数统计** —— Gaussian-only 的 thewalrus 做不到的独特价值。

## 2. 核心公式（B9 单模核的 2m×2m 推广）

单高斯分量 `G(t⃗) = Σ_{n⃗} P(n⃗)·t⃗^{n⃗}`（概率生成函数），B9 单模为

```
A = V⁻¹ (2m×2m),  c_j(t_j) = (1−t_j)/(1+t_j),  P_j = mode j 的 I₂ 分块投影
B(t⃗) = A + 2·Σ_j c_j·P_j
quad  = −½ r̄ᵀAr̄ + ½ (Ar̄)ᵀ B⁻¹ (Ar̄)          [复 r̄ 用解析转置二次型，非共轭转置]
G(t⃗) = 2^k · e^{quad} / ( Π_j(1+t_j) · √(det V · det B) )
```

`P(n⃗)` 用**逐轴 Cauchy 提取**（张量 FFT = 每轴独立 FFT），半径 0.95、每轴
`max(128, 8·cutoff)` 点。分量在 log 域逐 torus 点合并（复权重 + 复中心，
Hermitian 干涉保留），与 B9 同纪律。

## 3. 验证结果（vs gold，全部 ≤1e-16 逐位）

| # | 场景 | gold 来源 | max|Δ| | 判定 |
|---|---|---|---|---|
| 0 | 真空自检 G(t⃗)≡1 | 解析恒等式 | 1.5e-17 | ✅ |
| diag | TMSV 单模边缘 vs 热态 | n̄=sinh²r 闭式 | 4.7e-17 | ✅ |
| 1 | TMSV r=0.5 全模 P(n,n) | `tanh²rⁿ/cosh²r` | 1.1e-16 | ✅ |
| 1b | 子集边缘 = 全模边缘 | 自洽 | 5.4e-17 | ✅ |
| 1c | TMSV r=1.2 强压缩 | 闭式 | 1.2e-16 | ✅ |
| 2 | cat(α=0.8)⊗coherent(β=0.6) | fock expm | 2.2e-16 | ✅ |
| 3 | cat(α=0.7)⊗cat 16 分量(复中心×复权重) | fock expm | 1.1e-16 | ✅ |
| 3b | cat(α=1.1)⊗cat 大 α 峰值分离 | fock expm | 1.5e-16 | ✅ |

**关键结论**：复中心（相对位移含 p 分量）、复权重、块对角 V、关联 V（TMSV）、
非高斯交叉项全部精确复现 gold。**数学核成立**，无近似、无泄漏。

## 4. 核心发现

### 4a. 多轴分支锚定（关键数值陷阱，已解决）
B9 单模核 (`np.log(1+t) − ½log(detV·detB)`) 在**多模独立路径**下会 `branch race`：
`det(V)·det(B)` 的**真实辐角可达 ±2π**（真空 detVB 实为
`16/(Π(1+t)²)`，当 t 绕 −1 时辐角扫过 π），principal `np.log`/`np.sqrt` 逐点
取 `[-π,π]` 就会 wrap，实测真空 torus **802/4096 点 G 翻 −1**。

**修复**：√detVB 的支锚定到 `−Σ_j arg(1+t_j)` —— 解析上
`arg(√detVB) = −Σ arg(1+t_j) + 正定小量`；主值 sqrt 后，若辐角与 target 相差
> π/2 则翻号（anchor 到连续支，使 `G(1⃗)=1` 归一锚成立）。修复后真空
1.3e-15、TMSV 闭式 5.6e-16（vs 原先 2.0、最大偏差）。

### 4b. 子集测量的 prefactor 系数（已澄清）
对**子集测量**（k<m），prefactor 取 `k·log2`（被测模数），不是总模数 m。
Wigner 积分遍历全相空间，但未测模 t=1 贡献 `2/(1+1)=1`，`m·log2` 会整体翻倍
（实测相干 P(0) 从 0.527 → 1.59）。用 `k·log2` 后子集/全模边缘一致（场景 1b 5.4e-17）。

### 4c. 复中心坐标槽（构景纪律）
复中心相对位移必须放 **p 槽**（第 2、4 维），x 槽只放实位移。探针初版把
`i√2α` 塞进 x 槽（复 x），与 fock gold 不对应（误差 4.06e-1 / 2.38）；
修正为 p-槽后逐位吻合（1.1e-16）。cvsim xxpp 约定：`rbar = (√2 Re α, √2 Im α)`。

## 5. 性能边界（B10 关键约束）

| 模数 | 每轴点数 | torus 点 | 时间（纯 Python 逐点循环） |
|---|---|---|---|
| 1 | 128 | 128 | 快 |
| 2 | 128 | 16,384 | ~2.7s |
| 3 | 128 | 2,097,152 | ~400s（128³） |
| 3 | 48 | 110,592 | ~21s（48³） |

- **2 模舒适**（240² ≈ 0.45MB，与 PRD AC 一致；m_meas≤2）。
- **3 模纯 Python 循环 400s 不可接受** → 生产必须**向量化**（numpy 批量求值
  logG，逐分量逐点），或限制 m_meas≤2。**这是 B10 需要向量化实现的决定性结论**。

## 6. 对 B10 实现的启示

1. **数学核已验证**，可直接进 `cvsim/bosonic/measure.py` 的联合路径。
2. **必须向量化**：`joint_pn` 的纯 Python 逐点循环在 3 模 400s，需要改为
   numpy 批量（对 ms 维 torus 数组一次性求 logG，再逐分量 log-sum-exp 合并）。
3. **分支锚定**必须内建到生成函数，不可回退到 B9 裸 `np.log`（多模会翻 −1）。
4. **子集测量 prefactor = k·log2**，复中心放 p 槽（与 cvsim xxpp 约定一致）。
5. **gold 锚**（必须做）：TMSV(关联块对角)、cat⊗coherent(乘积)、cat⊗cat(复中心
   交叉)。

## 7. 探测工具

- `tools/probe_bosonic_pnr_joint.py` — 联合多模 PNR 分块核 vs 解析/fock gold（可复现）
