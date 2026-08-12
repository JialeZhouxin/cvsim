# GBS path: The Walrus adapter

**Status:** Phase 3 exit item #4 (vision §5 Phase 3 criterion 4)  
**Applies to:** `cvsim.gaussian.export_cov_for_walrus`, optional extra `cvsim[gbs]`  
**Date:** 2026-08-07

GBS 走 **adapter** 路线（vision L545）：不自研 Hafnian 内核（vision L546），
用 [The Walrus](https://github.com/XanaduAI/thewalrus) 做采样/概率计算。
`cvsim` 核心不依赖 thewalrus —— 它是 optional extra `cvsim[gbs]`。

## 约定

| Item | cvsim（输入） | The Walrus（输出） |
|------|----------------|---------------------|
| $\hbar$ | `1`（`cvsim.conventions.HBAR`） | 默认 `hbar=2`；σ 按真空 σ=I 归一化：σ = 2V/ħ = 2V |
| 正交序 | **xxpp**：$(x_1,\ldots,x_m,p_1,\ldots,p_m)$ | **xxpp 同序**（thewalrus ≥ 0.22 quantum 模块；0.22.0 实测确认） |
| 状态 | `GaussianState` (V, r̄) | 返回 `(σ, μ)`，长度 $2m$ |

`export_cov_for_walrus(state)` 返回 `(σ, μ)`：σ 已做 hbar=2 归一化（σ = 2V）；
μ = √2·r̄（thewalrus 用 SF 正交算符 $\hat x = \hat a+\hat a^\dagger$，真空方差 1；
cvsim 用 $\hat x=(\hat a+\hat a^\dagger)/\sqrt 2$，真空方差 ½）—— 这样 thewalrus 复原的
复振幅 $(\mu_{[:m]}+i\mu_{[m:]})/\sqrt{2\hbar}$ 恰好等于 α。

> **版本注（已实测，thewalrus 0.22.0）**：`thewalrus.quantum.density_matrix` /
> `photon_number_mean` 的 docstring 写 “xp-ordering”，但实现按 xxpp 块读取
> （`Qmat` 取 `cov[:N,:N]` 为 x 块）；双模 TMSV 对拍（P(n,n) 到 1e-9）确认
> **xxpp** 才是真实约定。适配器按装上的版本输出 xxpp，不置换。

输入不做物理性校验（与 `GaussianState` 构造一致），需要时先调
`cvsim.gaussian.validate_state`。

## 用法

```python
import numpy as np
from thewalrus.quantum import density_matrix, photon_number_mean
from cvsim.gaussian import GaussianState, export_cov_for_walrus

# 1) 构造状态（cvsim 电路）
st = GaussianState.squeezed(r=1.0)      # 单模压缩真空
# 多模也一样: GaussianState.tmsv(r=1.0)、
#   GaussianCircuit(1).squeeze(0, 1.0).compile().run()

# 2) 导出 thewalrus 格式
sigma, mu = export_cov_for_walrus(st)

# 3) 喂给 thewalrus：光子数分布 / 平均光子数
P = np.real(np.diag(density_matrix(mu, sigma, cutoff=6, hbar=2)))  # 单模 P(n)
nbar = photon_number_mean(mu, sigma, 0, hbar=2)                    # 模式 0 平均光子数
# 多模: density_matrix 返回 (D,D,...) 共 2m 维张量, P(n1,...,nm) = dm[n1,n1,...,nm,nm]
```

`cvsim[gbs]` 未安装时，对拍测试（`tests/test_walrus.py` 对拍层）自动 skip
（`pytest.importorskip`），格式层照跑 —— 核心 CI 不装 thewalrus 也能全绿。

## 薄封装（pnr_probs / gbs_sample / threshold_sample）

`cvsim.gaussian` 直接提供 thewalrus 的 GBS 概率/采样三件套（薄封装，
**延迟导入**：未装 `cvsim[gbs]` 时调用抛 `RuntimeError` 提示安装）。
用户无需记 ħ=2 / xxpp / σ=2V / μ=√2·r̄ 约定 —— 封装内部走
`export_cov_for_walrus`。

| API | 签名 | 输出 | 来源（thewalrus） |
|-----|------|------|-------------------|
| `pnr_probs` | `(state, cutoff)` | `[cutoff]^m` 联合分布 `P[n1..nm]`，float | `thewalrus.quantum.probabilities` |
| `gbs_sample` | `(state, n_samples, *, cutoff=5, max_photons=30)` | `(n_samples, m)` int64 PNR 样本 | `thewalrus.samples.hafnian_sample_state` |
| `threshold_sample` | `(state, n_samples, *, max_photons=30, fanout=10)` | `(n_samples, m)` int8 click pattern，值 ∈ {0,1} | `thewalrus.samples.torontonian_sample_state` |

```python
from cvsim.gaussian import GaussianState, pnr_probs, gbs_sample, threshold_sample

st = GaussianState.tmsv(r=0.5)
P = pnr_probs(st, cutoff=5)          # 形状 [5,5]；P.sum() < 1 是截断泄漏，不归一化
samples = gbs_sample(st, 1000)       # (1000, 2) int64
clicks = threshold_sample(st, 1000)  # (1000, 2) int8
```

注意：
- **RNG 不可注入**：thewalrus 内部用全局 `np.random`，三函数无 `rng=` 参数
  （与 cvsim 其他采样 API 风格不同，属上游约束）。
- `pnr_probs` 与 fock 侧 `pnrd_probs`（输入 `FockLike`）命名区分，docstring 互指。
- **ħ 固定 2**：`pnr_probs` 无 hbar 旋钮——`export_cov_for_walrus` 已归一化 σ=2V，
  传其他 hbar 会静默算错（OCR 2026-08-12）。
- 版本 pin `thewalrus>=0.22,<0.23`：0.22.x quantum 模块按 xxpp 读块
  （docstring 写 xp 已过时）；`<0.23` 防约定漂移。

## 范围

- **有**：adapter + 薄封装三函数（pnr_probs / gbs_sample / threshold_sample）+ 测试 + 本说明。
  GBS 路径 = 导出 + thewalrus 概率/采样。
- **无**：自研 Hafnian/Torontonian 内核、approximate GBS samplers（vision §4.3 P2）、
  GBS 教学 notebook（Phase 5）、GBS 应用算法。
