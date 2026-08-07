# F-SAMPLE batch — Implementation

## 依赖序

核心函数 → 测试 → 冻结 → 文档。单一 commit（小任务），OCR 后提交。

## 1. 实现（observables.py + state.py）

- [ ] `observables.py`：提取 `_heterodyne_params(state, mode) -> (mu, Sigma)`；`heterodyne_sample` 改用它（行为不变）
- [ ] `homodyne_sample_batch(state, mode=0, phi=0.0, size=1000, *, rng=None)`：μ/σ 复用 homodyne_mean/var，`rng.normal(mu, sigma, size=size)`；σ²≤EPS → ValueError；size 校验
- [ ] `heterodyne_sample_batch(state, mode=0, size=1000, *, rng=None)`：`rng.multivariate_normal(mu, Sigma, size=size)` → complex；size 校验
- [ ] `state.py`：`GaussianState.sample_quadratures(size, *, rng=None)`：`rng.multivariate_normal(self.rbar, self.V, size=size)`
- [ ] `__init__.py`：`__all__` 追加 3 符号
- verify: `python -c` 冒烟（真空 heterodyne batch 均值≈0，σ²≈½）

## 2. 测试（tests/test_observables_batch.py）

- [ ] R5：同 rng 序列 `size=1` batch == 单次 sample（homodyne 直接比；heterodyne 若 size=1 路径不同则改策略）
- [ ] 统计收敛：homodyne 压缩真空 φ=0：μ=0, σ²=½e⁻²ʳ（N=10⁵ atol≈0.02）；heterodyne 真空：⟨β⟩≈0, ⟨|β|²⟩≈1（N=10⁵ atol≈0.05）；quadratures：vacuum ⟨x²⟩≈½
- [ ] R5 golden：固定种子（default_rng(7)）→ 数组快照（首 8 元素）——vision §7.3
- [ ] size 校验：0/-1/1.5/"3" → ValueError
- [ ] σ²→0（真空 homodyne x 方向）：ValueError
- [ ] 向量化：rng.bit_generator 一次 normal 调用（spawn 后直接比较 bit 状态？——简化：monkeypatch `rng.normal`/`rng.multivariate_normal` 计数 == 1）
- [ ] `test_public_api.py`：3 符号入冻结表
- verify: `.venv/Scripts/python -m pytest tests/test_observables_batch.py -q`

## 3. 文档 + 收口

- [ ] `docs/api-stability.md` §2.2 加 sample_batch 行
- [ ] 全量 pytest + node 测试绿
- [ ] OCR review → high/medium 清零
- [ ] 选择性 git add → commit
- [ ] `task.py archive` + add_session.py 记录

## 风险

- heterodyne size=1 与单次 multivariate_normal 路径是否逐值一致——若否，R5 改「同种子重构造 rng 联合分布等价」并注明
- 统计测试 flaky：用 N=10⁵ + atol 3σ 区间，固定种子 → 确定值，不 flaky
