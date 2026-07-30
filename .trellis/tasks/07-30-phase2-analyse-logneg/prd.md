# F-ANALYSE-3: log_negativity

## Goal

实现 `log_negativity(state, modes_A) -> float`（bits），对 `modes_A` 做 partial transpose 后算对数负性。

## Decisions (math locked by literature + vision test freeze)

1. **单位 bits（log₂）** — 愿景明确 $\log_2$。
2. **公式（修正愿景字面）**：$\mathcal E_N=\sum_j\max\{0,-\log_2(2\tilde\nu_j)\}$  
   等价于只对 $\tilde\nu_j<1/2$ 求和。愿景字面 $-\sum_j\log_2(2\tilde\nu_j)$ 对全部 $j$ 在 TMSV 上正负抵消得 0，与 freeze 的解析式 $-\log_2(e^{-2r})$ 矛盾；**以解析 freeze 与 Weedbrook/Adesso 为准**，实现后应在 vision 记一笔 amend（或 docstring 注明）。
3. **PT**：对 `modes_A` 的 $p$ 轴乘 $-1$（$\Lambda V\Lambda$，$xxpp$）。
4. **谱**：PT 后必须用**无 vacuum-floor clip** 的 symplectic 谱；公开 `symplectic_eigenvalues` 的 clip 会把 $\tilde\nu_{\min}<1/2$ 抬回 0.5，毁掉 $E_N$。
5. **签名**：`log_negativity(state: GaussianState, modes_A: int | Iterable[int]) -> float`（需要完整 state；modes_A 为子系统 A）。

## Acceptance

- [ ] TMSV(r): $E_N = -\log_2(e^{-2r}) = 2r/\ln 2$
- [ ] vacuum / 可分 product thermal: $E_N=0$
- [ ] modes_A 与补集对称（$E_N(A)=E_N(A^c)$ for pure bipartite）
- [ ] 非法 modes raise
- [ ] pytest 全绿

## Out of scope

- fidelity / Heterodyne
- 不改变公开 `symplectic_eigenvalues` 默认 clip 行为（仅内部 raw 路径）
