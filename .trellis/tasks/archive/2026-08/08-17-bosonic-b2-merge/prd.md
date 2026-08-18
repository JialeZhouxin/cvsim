# B2.2 组件稳定合并

## Goal

实现稳定、可复现的近邻组件合并，并记录合并造成的几何畸变。

## Requirements

- 在 `cvsim/bosonic/component_eng.py` 实现 `merge(state, *, atol=1e-10, rtol=1e-8) -> (BosonicState, LeakReport)`。
- 按输入顺序稳定贪心分组：后续组件只与组内第一个代表比较。
- `V` 与复数 `rbar` 均用 `np.allclose` 判定；权重不参与分组。
- 每组保留第一个组件的 `V/rbar`，权重为组内权重之和。
- 不要求输入归一化、不自动归一化、不修改输入。
- 报告 `merge_groups` 与组内相对代表的最大 `V/rbar` 元素绝对差 `merge_distortion`。
- NaN/Inf 权重直接抛出 `ValueError`。

## Acceptance Criteria

- [ ] 等价组件合并且 `weight_sum` 不变。
- [ ] 复数均值/权重和 cat 风格共轭对可正确合并。
- [ ] 链式接近只按代表比较，不发生连通分量式过度合并。
- [ ] 无合并报告畸变为 0；多个组报告最大畸变。
- [ ] 边界 `atol/rtol` 与输入顺序稳定性有测试。
- [ ] 输入组件数组和权重保持不变。
