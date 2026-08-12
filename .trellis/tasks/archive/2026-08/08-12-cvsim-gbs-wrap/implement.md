# Implement Plan — GBS 薄封装

## 1. `cvsim/gaussian/walrus.py` 追加三函数

```python
def pnr_probs(state, cutoff, *, hbar=2.0) -> np.ndarray
def gbs_sample(state, n_samples, *, cutoff=5, max_photons=30) -> np.ndarray
def threshold_sample(state, n_samples, *, max_photons=30, fanout=10) -> np.ndarray
```

- 每个函数内部：
  ```python
  try:
      from thewalrus.quantum import probabilities  # 或 samples
  except ImportError as e:
      raise RuntimeError("cvsim GBS 需要 thewalrus: pip install cvsim[gbs]") from e
  ```
- 公共校验 helper `_require_state(state)`（TypeError + `isinstance(GaussianState)`）——复用 `export_cov_for_walrus` 同款防御
- 正整数校验 helper（cutoff/n_samples/max_photons/fanout ≥ 1，`_check_size` 类似物）
- docstring 写明：RNG 不可注入（thewalrus 用全局 np.random）；截断泄漏 P.sum()<1 正常；与 fock `pnrd_probs` 命名区分

## 2. `cvsim/gaussian/__init__.py`

- import 三函数，`__all__` 追加 `"pnr_probs", "gbs_sample", "threshold_sample"`（紧邻 export_cov_for_walrus 行）

## 3. `tests/test_walrus.py` 追加测试（同文件，沿用 format/comparison 双层）

格式层（无 thewalrus 也可跑）：
- 类型错误：np 数组 / 字符串 → TypeError
- 缺包错误：monkeypatch 挡住 import（如 `monkeypatch.setitem(sys.modules, 'thewalrus', None)` 方式或 importorskip 反用）→ RuntimeError 含 "cvsim[gbs]"

对拍层（importorskip thewalrus）：
- `pnr_probs` vs `density_matrix` 对角：TMSV r=0.5, cutoff=5, einsum('iijj->ij') 对拍 atol 1e-9；形状 [5,5]；sum<1
- `pnr_probs` vs 解析：单模压缩真空 P(2n) 公式（复用 `_squeezed_vac_p`）
- `gbs_sample`：TMSV r=0.5, 20000 样本 shape (20000,2) int64；频率 vs pnr_probs 归一化后 atol 0.01
- `threshold_sample`：同态 20000 样本 shape (20000,2) int8，值域 {0,1}；click 频率 vs 粗粒化 P(S)（2 模 4 pattern）atol 0.01
- 参数校验：cutoff=0 / n_samples=0 → ValueError

## 4. `docs/gbs-walrus.md` 增补

"薄封装"小节：三 API 表（签名/输出形状/来源函数）、用法示例、版本 pin 注（<0.23 防约定漂移）

## 5. 验证

- 本机 venv（已装 thewalrus 0.22.0 + numpy 2.4.6）：`pytest tests/test_walrus.py -q` 全绿
- 全量：`pytest -q`（基线 959 + 新增）
- ruff + mypy 过（如项目 CI 同款命令）
- 模拟缺包测试：monkeypatch 路径跑一遍

## 风险

- 20000 样本对拍测试耗时：hafnian 采样 2 模 cutoff 5 快（毫秒级），可控；若 CI 慢可降 5000
- `probabilities` 纯态快速路径（state_vector²）与混合态枚举路径不同——TMSV 是纯态，走快速路径；可加一个 thermal 混合态用例覆盖枚举路径（shape/对拍）
