# B4 — Bosonic 调和对账分层套件 Implement Plan

## 7 步执行

### Step 1: 新建 `cvsim/bosonic/analyse.py`

实现 `purity` + `pure_fidelity`：
- `purity(state, *, validate=False)`：遍历分量 `Σ |w_k|² / (2^m · √det V_k)`，复用 `_as_cov` 模式（直接读 `c.V`）；`validate=True` 走 `is_hermitian`；非物理 `det V_k ≤ 0` 抛错。docstring 标 teaching 对角近似 + 指向 `overlap`。
- `pure_fidelity(state_a, state_b)`：验 V 等同（每分量 `allclose`）→ 构 Gram `T[i,j] = _gauss_overlap(V, r_i^a, r_j^b)`（从 gkp.py import `_gauss_overlap`）→ `c_a = np.sqrt(w_a)`（complex）→ `inner = c_a.conj() @ T @ c_b` → `return float(abs(inner)**2)`。docstring 标等 V 限制 + B7 升级路径。

验证：`python -c "from cvsim.bosonic import purity, pure_fidelity; ..."` 无报错。

### Step 2: 公共面

- `cvsim/bosonic/__init__.py`：`__all__` +`purity` +`pure_fidelity`，import from `.analyse`
- `pyproject.toml`：`markers` +`phaseB4: Bosonic B4 reconciliation suite`
- `tests/test_public_api.py`：BOSONIC_PUBLIC set +`purity` +`pure_fidelity`

验证：`python -c "import cvsim.bosonic as b; print(b.purity, b.pure_fidelity)"`。

### Step 3: `tests/test_b4_bosonic_reconciliation.py` — layer 1 (L1a-L1e)

全 `@pytest.mark.phaseB4`。helper 复用 B3 的 `_fock_pdf`。
- L1a: K=1 squeezed r=0.6 → `purity` vs `gaussian.purity`，`homodyne_var` vs gaussian atol 1e-12
- L1b: K=1 coherent 0.7+0.3j → `mean_photon` vs |α|² atol 1e-12
- L1c: K=2 thermal-like（两 coherent，w=0.5/0.5）→ `purity` vs `Σ|w|²·1/(2^m√detV)` 自洽 atol 1e-7
- L1d: cat even α=2.0 → `mean_photon` vs `|α|²*(1-exp(-2*|α|²))/2 + 0.5`（含 vacuum 贡献）atol 1e-7
- L1e: cat even α=2.0 vs `FockState.cat(cutoff=30)` → `homodyne_pdf` 网格点 atol 1e-7

验证：`pytest tests/test_b4_bosonic_reconciliation.py -m phaseB4 -k L1 -q`。

### Step 4: layer 2 (L2a-L2e)

- L2a: `pure_fidelity(gkp0, gkp0)` atol 1e-10
- L2b: `pure_fidelity(gkp1, gkp1)` atol 1e-10
- L2c: `pure_fidelity(gkp0, gkp1)` vs `abs(gkp_logical_overlap(gkp0, gkp1))**2`，`cross="none"` atol 1e-7
- L2d: gkp0 → homodyne 测 x 模（phi=0）→ condition 得 post → 位移回最近格点 → `pure_fidelity(post, gkp0)` atol 1e-6
- L2e: gkp0 → loss γ=0.1 → assert `pure_fidelity(lossed, gkp0) < 1.0`（定性，无 atol）

验证：`pytest tests/test_b4_bosonic_reconciliation.py -m phaseB4 -k L2 -q`。

### Step 5: 全套回归

`pytest -q` → 期望 1094 + (B4 新增 ~10-12) passed。

### Step 6: spec 更新

`.trellis/spec/cvsim/bosonic.md` §6.x（新增 B4 节）：
- `purity`/`pure_fidelity` 签名 + teaching 限制 + 等 V 限制
- layer 1/2 对账套件结构
- `gkp_logical_overlap` deprecated 指向 `pure_fidelity` 已落地

### Step 7: commit + 归档

`feat(bosonic): B4 调和对账——purity/pure_fidelity 闭式 + R1 分层对账套件`

## 风险/回退点

- `analyse.py` 新文件，零修改既有代码 → 低风险
- `_gauss_overlap` 从 gkp.py import：跨子模块 import（同包内，不违反 ADR-0001）
- L1d cat mean_photon 解析公式需确认（含 vacuum 0.5 贡献？查 Gaussian `mean_photon` 实现）
- L2d homodyne 测 x 模 + 位移回格点的物理流程需对齐 GKP 教学约定

## 验证命令

```powershell
.venv\Scripts\python.exe -m pytest tests/test_b4_bosonic_reconciliation.py -m phaseB4 -q
.venv\Scripts\python.exe -m pytest -m phaseB4 -q
.venv\Scripts\python.exe -m pytest -q
```
