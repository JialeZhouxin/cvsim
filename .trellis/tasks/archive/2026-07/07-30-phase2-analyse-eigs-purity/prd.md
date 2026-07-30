# F-ANALYSE-1: symplectic_eigenvalues + purity

## Goal

实现 Phase 2 F-ANALYSE 依赖根的两个函数：
- `symplectic_eigenvalues(state) -> np.ndarray`：返回 $m$ 个 symplectic 特征值 $\nu_j\ge 1/2$（升序）。
- `purity(state) -> float`：返回 $\mu=1/(2^m\sqrt{\det V})$，纯态 $=1$。

实现后 F-ANALYSE 下游（entropy_vn / log_negativity / fidelity）的数值根立稳。本任务**只做这两个函数 + 测试**，不触碰下游。

## Background

- 愿景 §4.2 F-ANALYSE 七函数中 `is_physical` 已实现 (`analyse.py:11`)；本切片补依赖根 `symplectic_eigenvalues` + `purity`。
- Phase 2 退出第 1 条"研究量匹配解析 TMSV/thermal"——本切片覆盖 vacuum purity 1、thermal purity $1/(2\bar n+1)$、thermal symplectic eigval $\bar n+1/2$。
- 愿景 §9 测试教义：unit（math identity）+ invariant（purity/symplecticity）+ golden（fixed seed snapshot）。

## Confirmed facts (from codebase + numerical experiments)

- `is_physical` 已实现 (`analyse.py:11`)，用 `V + iΩ/2 ≽ 0` 判据；`omega` 来自 `conventions.omega`。
- `det_cov(state)` 已有 (`observables.py:12`)，用 `np.linalg.det`（无 slogdet 稳定版）。
- `GaussianState` 有 `.V`（协方差）、`.rbar`（均值）、`.nmode`。
- **算法 evidence (实测, 2026-07-30)**：
  - `|eig(iΩV)|` 与 Cholesky-Williamson 两路径对 vacuum / thermal / TMSV / loss 后态数值一致。
  - 纯态 TMSV($m=2,r=0.6$)：全部 $\nu_j=1/2$。
  - thermal $\bar n=0.5$：$\nu=[1.0]=\bar n+1/2$。
  - thermal product $\bar n=\{0.3,1.0\}$：$\nu=[0.8,1.5]$（取每对 $\pm\nu$ 的一个：`sorted(|Re|)[::2]`）。
  - 误用 `nu[m:]`（取上半）会把 `[0.8,0.8,1.5,1.5]` 错取成 `[1.5,1.5]`——正确是 `[::2]`。
  - purity slogdet：vacuum=1、thermal 0.5=0.5、TMSV pure≈1、TMSV+loss≈0.794 <1。

## Decisions (brainstorm resolved)

| Q | 决定 | 理由 |
|---|------|------|
| Q1 算法 | **Williamson 分解 (Cholesky 路径)** | 用户主动选稳健路径；任意物理 V 可对角化 |
| Q2 purity | **slogdet** | 愿景 §7 明确要求；为 Phase 3 m=100 预埋 |
| Q3 签名 | **对齐 is_physical**：`GaussianState \| np.ndarray` | 接口一致，测试便利 |
| Q4 validate | **不强制**，但 clip/guard | ν clip ≥1/2；purity 对 slogdet sign≤0 raise |

## Requirements

1. `symplectic_eigenvalues(state) -> np.ndarray`：返回 $m$ 个 $\nu_j\ge 1/2$（升序 float64）。算法用 Cholesky-Williamson（见 design.md）。
2. `purity(state) -> float`：$\mu=1/(2^m\sqrt{\det V})$，用 `slogdet`。
3. 两个函数放进 `cvsim/gaussian/analyse.py`（与 `is_physical` 同文件）。
4. 公开导出 `cvsim/gaussian/__init__.py`。
5. docstring 写明愿景 §4.2 数学定义 + cite 算法（Williamson / Serafini）。
6. 纯态：所有 $\nu_j=1/2$（atol）；purity $=1$（atol）。
7. 边界 guard：ν clip `≥ 0.5`；purity 对 `slogdet` sign≤0 raise `ValueError`。
8. 不强制调用 `validate_state`（调用方自管）。

## Acceptance Criteria

- [ ] `symplectic_eigenvalues` 与 `purity` 在 `analyse.py` 实现并导出。
- [ ] `tests/test_analyse.py` 新增，覆盖：
  - vacuum: purity=1, sym_eig 全 0.5
  - thermal $\bar n$: purity $1/(2\bar n+1)$, sym_eig $[\bar n+1/2]$
  - TMSV（纯态）: purity=1, sym_eig 全 0.5
  - loss 后态（混合）: purity < 1, sym_eig $\ge 1/2$
  - 多模 thermal product: sym_eig 长度 $m$, 各模独立正确值
  - 裸 `np.ndarray` 输入路径
  - purity 对非 PD V（sign≤0）raise
- [ ] `pytest -q` 全绿（现有 296 + 新增 ≥7）。
- [ ] docstring 含愿景 §4.2 数学定义 + 算法 cite。

## Technical Notes

- **Williamson 定义**：对物理协方差 $V$，存在辛矩阵 $S$ 使 $S V S^\mathsf T = \bigoplus_{j=1}^m \nu_j I_2$，其中 $\nu_j\ge 1/2$ 为 symplectic eigenvalues。
- **Cholesky 路径**（Serafini / Weedbrook 标准实现）：
  1. symmetrize $V\leftarrow\frac12(V+V^\mathsf T)$
  2. $K=\mathrm{chol}(V)$（$V=KK^\mathsf T$；近奇异纯态加 $10^{-14}I$ jitter）
  3. $A=K^\mathsf T\Omega K$（斜对称）
  4. $\lambda_j=\mathrm{eig}(iA)$（实数 $\pm\nu$）
  5. $\nu=\mathrm{sort}(|\mathrm{Re}\,\lambda|)[::2]$（每对取一个，升序）
  6. clip $\nu\leftarrow\max(\nu,\,0.5)$
- **purity**：$\mathrm{sign},\ell=\mathrm{slogdet}(V)$；sign≤0 → raise；$\mu=\exp(-\ell/2)/2^m$。
- **交叉验**：purity 也可由 $\prod_j(1/(2\nu_j))$ 算出，单测可对照两条路径（可选，非强制）。

## Out of scope

- 不实现 entropy_vn / log_negativity / fidelity / partial_trace（后续切片）。
- 不实现 Heterodyne（F-MEASURE-FULL）。
- 不改 `det_cov`（保持 `np.linalg.det`；新 `purity` 走 slogdet 独立路径）。
- 不写教学 notebook（Phase 2 收尾切片统一做）。
