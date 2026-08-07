# F-SAMPLE batch 批量采样

## Goal

vision §4.2 F-SAMPLE：核心层批量采样——Homodyne / Heterodyne / Gaussian 正交分量采样。`size=10³` 标准（F-PERF：10⁵ stress 可选），向量化一次 RNG 调用，`rng=` 注入可复现（vision §3），测试固定种子 + golden 快照。

## Background（已确认事实）

- 现有单次 API（`cvsim/gaussian/observables.py`，api-stability §4 冻结）：`homodyne_sample` / `heterodyne_sample`（不条件）、`homodyne_sample_and_condition` / `heterodyne_sample_and_condition`（条件+删模）
- `heterodyne_sample` 已用 `rng.multivariate_normal(mu, Sigma)`——批量 = 一次 `size=n` 调用
- API 稳定性：现有函数返回类型（float/complex）冻结——批量必须**独立新函数**（§2.1：改返回类型 = MAJOR）
- lab `/sample` 单次（seed 复现）——**本任务不动 lab**

## Requirements（brainstorm 收敛）

- R1: `homodyne_sample_batch(state, mode=0, phi=0.0, size=1000, *, rng=None) -> np.ndarray (size,)`
  - 从同一边缘分布采 N 个 iid outcome（无逐 shot 条件）
  - 方差下限检查同单次（σ²≤EPS → ValueError，deterministic 与 shot 无关）
- R2: `heterodyne_sample_batch(state, mode=0, size=1000, *, rng=None) -> np.ndarray (size,)，dtype=complex`
  - 返回 complex 数组与单次 `heterodyne_sample` 返回 complex 一致
- R3: `GaussianState.sample_quadratures(size, *, rng=None) -> np.ndarray (size, 2m)`（xxpp 序，全态高斯正交分量批量）
- R4: 全部向量化（`rng.normal` / `rng.multivariate_normal(..., size=n)` 一次调用）
- R5: 与单次采样一致：同 `rng` 下 `sample_batch(..., size=1)` 数值等于 `sample(...)`
- R6: `size` 参数校验：正整数（`size<1` → ValueError）

## Acceptance Criteria

- [ ] 3 个批量函数实现 + 文档字符串（公式 + xxpp 约定）
- [ ] `size=1` 与单次采样数值一致（同 rng 序列）——R5
- [ ] 统计收敛测试：大 N（10³/10⁵）样本均值/方差收敛到解析值（homodyne: μ=u·r̄, σ²=uᵀVu；heterodyne: μ=β, Σ=½I 真空）
- [ ] 固定种子 golden 快照测试（vision §7.3）
- [ ] 向量化验证：batch 只用 O(1) 次 RNG 调用（可测 rng.bit_generator 状态跳跃或 monkeypatch 计数）
- [ ] `test_public_api.py` 冻结新增函数 + `__all__` 更新
- [ ] 全量 pytest 绿；每 commit OCR high/medium 清零

## Out of Scope

- GBS / Walrus interop（gbs-decision 任务）
- GPU / JAX 批量（F-AD 任务）
- lab `/sample` n_shots + 前端分布视图（未来独立任务）
- 批量条件状态（outcome-only 已锁定，brainstorm Q1）

## Notes

- 命名后缀 `_batch` 与现有 `sample`/`sample_and_condition` 并列；api-stability §2.2「thin/may grow」新增条目
- `sample_quadratures` 放 `GaussianState` 方法（态固有操作），observables 函数只做单模边缘批量
