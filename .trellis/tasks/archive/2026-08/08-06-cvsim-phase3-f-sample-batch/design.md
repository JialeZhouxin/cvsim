# F-SAMPLE batch — Design

## Architecture

纯核心层新增，无新依赖，无 lab/前端改动。

```
cvsim/gaussian/observables.py     # + homodyne_sample_batch / heterodyne_sample_batch
cvsim/gaussian/state.py           # + GaussianState.sample_quadratures
cvsim/gaussian/__init__.py        # + __all__ 更新
tests/test_observables_batch.py   # 新测试文件
tests/test_public_api.py          # 冻结新符号
```

## Contracts

### `homodyne_sample_batch(state, mode=0, phi=0.0, size=1000, *, rng=None) -> np.ndarray`

- 每 shot：outcome ~ N(μ, σ²)，μ = u·r̄，σ² = uᵀVu，u = (cosφ, sinφ) 映射到 xxpp 的 mode 槽位
- 向量化：`rng.normal(mu, sigma, size=size)`
- σ² ≤ EPS → `ValueError`（同单次语义）
- `size` 校验：`isinstance(size, int) and size >= 1`，否则 `ValueError`

### `heterodyne_sample_batch(state, mode=0, size=1000, *, rng=None) -> np.ndarray`

- 每 shot：β ~ 边缘高斯（当前实现 `heterodyne_sample` 的 mu/Sigma），复值
- 向量化：`rng.multivariate_normal(mu, Sigma, size=size)` 一次 → 转 complex
- 与单次 `heterodyne_sample` 共享内部 helper（提取 `_heterodyne_mu_sigma(state, mode)`，单次/批量共用——避免公式漂移）

### `GaussianState.sample_quadratures(size, *, rng=None) -> np.ndarray (size, 2m)`

- 整态 xxpp 正交分量：`rng.multivariate_normal(self.rbar, self.V, size=size)`
- 与 heterodyne 的 ½ 缩放语义无关（这是直接正交分量，非 POVM 投影）

## 数值/复现

- R5 一致性：`rng.normal(mu, sigma, size=1)` 与单次 `rng.normal(mu, sigma)` 同 rng 下首样本相等（numpy 保证）
- heterodyne：单次 `multivariate_normal(mu, Sigma)` vs 批量 `multivariate_normal(mu, Sigma, size=1)`——numpy 对 size=1 用同一采样路径（需测试实证；若有偏差，R5 测试用「同种子重新构造 rng」策略，比较联合分布而非逐值）
- golden 快照：固定种子 + 固定 state → 期望数组硬编码（首 8 元素 + 全数组 hash 可免）

## 共享 helper 提取（防漂移）

`observables.py` 内私有：
- `_homodyne_mu_var(state, mode, phi) -> (mu, var)`（homodyne_mean/var 已有，复用即可，不新提取）
- `_heterodyne_params(state, mode) -> (mu, Sigma)`：从现有 `heterodyne_sample` 提取，单次/批量共用

## Trade-offs

| 选项 | 结论 |
|------|------|
| 独立函数 vs 现有函数加 size= | 独立函数（api-stability §2.1：改返回类型 = MAJOR） |
| complex vs (size,2) float | complex (size,)（与单次返回类型一致，R5 直接可比） |
| batch 条件状态 | 不做（outcome-only，PRD Q1） |

## Compatibility

- 纯新增：现有 568 测试不动；`__all__` 追加 3 符号（MINOR，非 MAJOR）
- `heterodyne_sample` 内部重构（helper 提取）不改变其行为——test 冻结保护
