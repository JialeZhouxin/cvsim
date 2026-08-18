# B3 Implement — 执行计划

> 前置：prd.md + design.md 已审。物理事实源 vision §2.3 + ADR-0006。

## 执行顺序

### 1. `homodyne_pdf` 实现（observables.py）

- 新增 `homodyne_pdf(state, mode=0, phi=0.0, *, n_grid=None, lim=None) -> (xs, P)`。
- 内部：算每分量 `μ_k = u·r̄_k`（complex）、`σ²_k = uᵀ V_k u`（float）；网格自动规则（§2.2）；`S = Σ_k w_k p_k(x)`（complex）；`is_hermitian` 兜底 Im≈0；`P = max(Re S, 0)`；负 Re warn。
- 复用现有 `_homodyne_u` / `_check_mode` / `_SIG_EPS`。
- verify: `pytest tests/test_b3_bosonic_homodyne_exact.py::test_pdf_k1_gaussian -q`（K=1 退化单高斯 atol=1e-12）

### 2. `homodyne_sample` 重写（observables.py）

- 删旧实峰池逻辑（`_POOL_IMAG_TOL` 过滤 + `rng.choice` + `rng.normal`）。
- 新实现：调 `homodyne_pdf` → CDF cumsum → `searchsorted` 反演。签名加 `n_grid`/`lim`/`shots`，返回 `np.ndarray (shots,)`。
- verify: `pytest tests/test_b3_bosonic_homodyne_exact.py::test_sample_histogram_cat -q`（判据 3）

### 3. `homodyne_sample_and_condition` 升级（observables.py）

- 签名补 `n_grid`/`lim`/`shots`；调新 sample 取 `outcomes[0]` → condition。
- verify: 手动调一次确认返回 `(ndarray, BosonicState)`。

### 4. 公共面 + marker

- `cvsim/bosonic/__init__.py`：`__all__` +`homodyne_pdf`，import 同步。
- `measure.py`：re-export `homodyne_pdf`；docstring 去"teaching cut"标注（homodyne_sample 不再是教学切）。
- `pyproject.toml`：`markers` +`phaseB3: Bosonic B3 measurement precision tests`。
- `tests/test_public_api.py`：`BOSONIC_PUBLIC` +`homodyne_pdf`。
- verify: `pytest tests/test_public_api.py -q` + `pytest -m phaseB3 -q --co`（marker 可见）

### 5. 测试文件 `tests/test_b3_bosonic_homodyne_exact.py`

- 判据 1 cat 交叉核对（vs Fock cutoff=30，atol=1e-7）
- 判据 1 GKP 定性对齐（峰位/周期）
- 判据 2 Born 一致性解析核验（cat/相干/热，atol=1e-7）
- 判据 3 采样直方图（cat 10⁴ shots，bin 相对误差 <5%）
- K=1 Gaussian 对齐（atol=1e-12）
- 全标 `@pytest.mark.phaseB3`
- verify: `pytest tests/test_b3_bosonic_homodyne_exact.py -q`

### 6. 现有测试适配

- `test_b1_bosonic_measures.py` / `test_bosonic_condition.py` 等：`homodyne_sample` 返回类型 float→ndarray，取 `[0]` 或首元素适配。
- verify: `pytest tests/test_b1_bosonic_measures.py tests/test_bosonic_condition.py -q`

### 7. 全套回归

- `pytest -q`（全套绿，含 B1/B2 专项无破坏）
- `pytest -m phaseB3 -q`（B3 切片绿）

## 验证命令

```powershell
.venv\Scripts\python.exe -m pytest tests/test_b3_bosonic_homodyne_exact.py -q
.venv\Scripts\python.exe -m pytest -m phaseB3 -q
.venv\Scripts\python.exe -m pytest -q
```

## Review gates

- 步骤 1-2 后：主会话复验 `homodyne_pdf` + `homodyne_sample` 单元测试绿。
- 步骤 5 后：主会话复验 B3 专项全绿 + 出口判据全达。
- 步骤 7 后：trellis-check 子代理质量检查 → spec 更新 → OCR → commit。

## Rollback points

- 步骤 2 后若 Born 一致性失败 → 回 design §2 数学检查（μ_k 复值路径）。
- 步骤 6 若现有测试大面积破坏 → 评估返回类型变更影响面，必要时 `homodyne_sample` 加 `shots=None` 兼容旧调用（返回 float）。
