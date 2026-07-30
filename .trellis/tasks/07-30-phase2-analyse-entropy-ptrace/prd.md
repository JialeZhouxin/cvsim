# F-ANALYSE-2: entropy_vn + partial_trace

## Goal

实现 Phase 2 F-ANALYSE 下一刀：
- `entropy_vn(state) -> float`：von Neumann 熵 $\sum_j g(\nu_j)$（**nats**）
- `partial_trace(state, keep) -> GaussianState`：保留 `keep` 模，drop 其余（无测量坍缩）

## Decisions

| Q | 决定 |
|---|------|
| Q1 单位 | **nats (ln)**；$g(\nu)=(\nu+\frac12)\ln(\nu+\frac12)-(\nu-\frac12)\ln(\nu-\frac12)$；$\nu=\frac12\Rightarrow g=0$ |
| Q2 位置 | 均在 **`analyse.py`** 模块函数 |
| Q3 entropy 签名 | 对齐 purity：`GaussianState \| ndarray` + `validate: bool = False` |
| Q4 ptrace 签名 | **只接 `GaussianState`**，返回 `GaussianState` |

## Requirements

1. `entropy_vn`：内部 `symplectic_eigenvalues(..., validate=validate)`，再 $\sum g(\nu_j)$；$\nu=\frac12$ 数值稳定（$n=\nu-\frac12\le\varepsilon\Rightarrow g=0$）。
2. `partial_trace(state, keep)`：`keep` 为逻辑模索引（可迭代 int）；去重排序后一次 xxpp 切片 $V,\bar r$；非法索引 / 空 keep / 越界 raise。
3. 导出 `cvsim.gaussian`。
4. docstring：愿景数学、$g$ 定义、单位 nats、ptrace ≠ 测量 conditioning。

## Acceptance Criteria

- [ ] vacuum / 纯 TMSV：$S=0$
- [ ] thermal $\bar n$：$S=(n+1)\ln(n+1)-n\ln n$（$n=0\Rightarrow 0$）
- [ ] TMSV 约化单模熵 = thermal$(\sinh^2 r)$ 熵
- [ ] `partial_trace` 保留模数与 $V$ 块正确；与逐次 `remove_mode`（无关联时）一致
- [ ] 非法 keep raise；`validate=True` 非物理 raise
- [ ] pytest 全绿

## Out of scope

- log_negativity / fidelity / Heterodyne
- 不改 `remove_mode` 对外语义
