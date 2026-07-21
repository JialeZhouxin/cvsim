# Design · gap-fill 包 A

## Architecture

```text
父 07-21-cvsim-gap-fill (planning → tracking)
  ├─ child G1 fock-wigner      (no dep)
  ├─ child G2 density-gates    (no dep on G1; shares fock/)
  ├─ child G3 sample+cond      (uses existing G/B sample+condition)
  └─ child G4 uat-p0-close     (depends: G1+G2+G3 done)
```

## G1 · Fock Wigner（公式卡）

单模 ħ=1；α 与正交：

\[
\alpha=\frac{x+ip}{\sqrt2}.
\]

密度矩阵 \(\rho_{nm}=\langle n|\rho|m\rangle\)。教学用 **Fock 基展开**（Cahill–Glauber / 标准数基 Wigner 核）：

- 实现：对每个网格点 \(\sum_{n,m}\rho_{nm} W_{nm}(x,p)\)，\(W_{nm}\) 用关联 Laguerre 或等价稳定递推
- **检查点**
  - 真空：\(W(0,0)=1/\pi\)
  - \(\lvert1\rangle\)：原点 \(W(0,0)<0\)
  - 纯相干 / 小挤：网格中心区逼近 Gaussian `wigner_grid`（atol 松）

API 形态（子任务定名）：

```text
wigner_fock(state: FockState|FockDensity, x, p) -> float
wigner_grid 扩展接受 Fock*
```

**禁止** 在理论 MD 写函数名（工程 README 可写）。

## G2 · FockDensity 门

现有 pure：`gates.py` 建 \(U\) 作用于 amps。  
ρ 门：

\[
\rho' = U \rho U^\dagger.
\]

- 复用同一截断矩阵（displace/phase/squeeze 的 U）
- 签名：`displace(rho, α)` 等 overload，或 `apply_unitary(rho, U)`
- **检查点**
  - pure→ρ 后 D/R/S ≡ pure 门再 `from_pure`（Frobenius）
  - `loss` 后再 `displace`：`Trρ=1`，⟨n⟩ 有限

**本切片不做**：Kerr/BS on ρ；2 模 ρ。

## G3 · sample_and_condition

选项（子任务锁一个）：

| 选项 | 内容 |
|------|------|
| **A 薄 API** | `homodyne_sample_and_condition(state, …, rng) -> (outcome, state')` = sample + condition |
| **B 仅 demo** | `demos/m5_sample_condition.py` 两行组合，无新符号 |

推荐 **A**：一行封装，诚实文档写「组合非新物理」。

## G4 · UAT 收口

- 新场景 **U9**（或并入扩展）：Fock W(0,0)；ρ 门 smoke；sample+cond smoke
- 改 `USER_ACCEPTANCE` 未做列表
- README 能力矩阵 + pytest 计数
- `python -m cvsim.demos.user_acceptance` 全绿

## Docs touch map

| 文件 | G1 | G2 | G3 | G4 |
|------|----|----|----|-----|
| `cvsim/wigner.py` | ✓ | | | |
| `cvsim/fock/gates.py` 等 | | ✓ | | |
| `cvsim/gaussian|bosonic/observables` | | | ✓ | |
| `tests/` | ✓ | ✓ | ✓ | |
| `USER_ACCEPTANCE` / README | | | | ✓ |
| 理论 `*.md` | 默认不动 | | | |

## Risk

| 风险 | 缓解 |
|------|------|
| Fock Wigner ħ/α 约定错 | 钉 vac 1/π + \|1⟩ 负 |
| ρ 门与 pure 不一致 | 对照测试 |
| 范围爬到 P1 | 父 prd Won't 硬拦 |
