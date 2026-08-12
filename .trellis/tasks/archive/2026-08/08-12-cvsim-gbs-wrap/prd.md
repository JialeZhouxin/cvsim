# GBS 薄封装: pnr_probs + gbs_sample + threshold_sample

## Goal

给 cvsim.gaussian 增加 thewalrus 的**薄封装 API**（延迟导入，依赖仍为 optional extra `cvsim[gbs]`）：
用户不用记 thewalrus 约定（ħ=2、xxpp、μ=√2·r̄），直接用 `GaussianState` 拿 P(n) 联合分布和 GBS 采样。

**范围外**：不自研 Hafnian/Torontonian 内核；不封装 hafnian 手工计算（`hafnian_repeated` 等）；不改 pyproject 依赖结构（`thewalrus>=0.22,<0.23` 继续留在 `cvsim[gbs]`）。

## Requirements

### 新公共 API（cvsim/gaussian/walrus.py 内追加）

1. `pnr_probs(state, cutoff) -> np.ndarray`
   - PNR 联合分布，形状 `[cutoff]^m`（m = 模数），`P[n1,...,nm]` = 测到 (n1..nm) 光子的概率
   - 实现：`from thewalrus.quantum import probabilities`；`probabilities(mu, sigma, cutoff, hbar=2)`
   - 截断语义：nᵢ ∈ {0..cutoff−1}；`P.sum() < 1` 是正常截断泄漏，不归一化
2. `gbs_sample(state, n_samples, *, cutoff=5, max_photons=30) -> np.ndarray`
   - PNR 采样，形状 `(n_samples, m)`，dtype int64
   - 实现：`from thewalrus.samples import hafnian_sample_state`
3. `threshold_sample(state, n_samples, *, max_photons=30, fanout=10) -> np.ndarray`
   - threshold 采样（click pattern），形状 `(n_samples, m)`，dtype int8
   - 实现：`from thewalrus.samples import torontonian_sample_state`

### 约束

- **延迟导入**：三个函数内部 import thewalrus（`try/except ImportError` → `RuntimeError`，提示 `pip install cvsim[gbs]`）；模块顶层不 import
- **输入校验**：`state` 必须是 `GaussianState`（`TypeError`，与 `export_cov_for_walrus` 一致）；`cutoff`/`n_samples`/`max_photons`/`fanout` 正整数校验
- **RNG 不可注入**：thewalrus 内部用全局 `np.random`，签名无 rng 参数 → docstring 注明（与 cvsim 其他采样 API 的 rng 风格不同，属上游约束）
- 命名：`pnr_probs` 与 fock 侧 `pnrd_probs` 区分（fock 输入是 FockLike；gaussian 输入是 GaussianState），docstring 互指
- `__init__.py` 的 `__all__` 追加三名字；不动现有导出

### 文档

- `docs/gbs-walrus.md` 增补"薄封装"小节（API 表 + 用法示例 + 版本 pin 说明）

## Acceptance Criteria

- [ ] AC1: 三个新函数在无 thewalrus 环境下 import 成功（cvsim 本体不依赖 thewalrus）
- [ ] AC2: 无 thewalrus 时调用 → RuntimeError 提示 `pip install cvsim[gbs]`（测试用 monkeypatch 模拟缺包）
- [ ] AC3: `pnr_probs` 与 thewalrus `density_matrix` 对角一致（对拍 atol 1e-9），形状 `[cutoff]^m`
- [ ] AC4: `gbs_sample` 输出形状 (n_samples, m) int64；样本频率 vs `pnr_probs` 理论分布一致（容差宽松，如 20000 样本、atol 0.01）
- [ ] AC5: `threshold_sample` 输出形状 (n_samples, m) int8，值 ∈ {0,1}；click 频率 vs 粗粒化 P(S) = Σ_{n: nᵢ>0⇔i∈S} P(n) 一致（容差宽松）
- [ ] AC6: 参数校验错误（非 GaussianState、非正整数 cutoff 等）抛正确异常
- [ ] AC7: 新测试不装 thewalrus 也能跑（格式层照跑，对拍层 importorskip——沿用 tests/test_walrus.py 现有模式）
- [ ] AC8: 全量 pytest 绿（含既有 959 基线）
- [ ] AC9: `__all__` 冻结更新（三新名字）

## Notes

- 设计依据（多轮讨论已确认）：薄封装零风险（纯胶水）；风险全在 thewalrus 依赖约束（numpy>=2.0 / numba / sympy / dask），已由 optional extra 隔离；版本 pin `>=0.22,<0.23` 防约定漂移（0.22.0 docstring 写 xp 实际 xxpp，已实测）
- 上游约定速查：ħ=2、xxpp 序、σ=2V、μ=√2·r̄（见 docs/gbs-walrus.md）
- thewalrus 拒绝逻辑：`max_photons` 超限或触 cutoff 时内部 -1 重采，输出行数恒等于 n_samples（封装不需处理）
