# Design — Phase F4: Fock differentiable designer

## 目标与边界

Vision F4 三件套：`backend=` 参数化门 / Fock AD（squeeze/BS/Kerr 梯度）/ 一个优化 notebook。
单任务、3 commit。现有 193 Fock 测试 = 回归面（默认参数向后兼容，零调用方改动）。

## 架构（2026-08-12 修正：ADR-0001 约束）

**硬约束**：`test_architecture.py` AST 扫描 — rep 包 `cvsim.fock` 只允许 import `conventions/symplectic/circuit_common`；`cvsim.backend` 不在白名单（ADR-0001 spec "Module placement"：凡需要 backend 的模块必须顶层）。Gaussian 先例同构：`gaussian/gates.py` 零 backend 命中，backend 化在顶层 `symplectic.py`（矩阵级）+ `cvsim/ad.py`（链）。

→ Fock 侧镜像：**新建顶层 `cvsim/fock_ad.py`**（cvsim/ad.py 的 Fock 对应物），不在 fock 包内；fock 包零改动。

### 1. `cvsim/fock_ad.py` — 可微 U 镜像 + 目标链（commit 1）

镜像 Gaussian `cvsim/ad.py` 结构（`backend:` 首参 + `_get_xp` 分发 + 与上游公式交叉注释），**numpy 路径复用 fock 包真源**（不重复公式）：

```python
squeeze_u(backend, N, r)      # numpy → cvsim.fock.gates._squeeze_U（真源）；jax → jnp 镜像 expm(0.5r(a²−a†²))
bs_u(backend, N, theta, phi)  # numpy → fock 门公式；jax → jnp 镜像
kerr_diag(backend, N, chi)    # 对角相位，np/jnp 同式
cat_fidelity(backend, r, chi, *, alpha, T=1.0, cutoff=12)  # 全链：U→|0⟩→ρ→loss→猫保真度
bs_overlap(backend, theta, *, cutoff=8)  # BS 梯度测试链：|1,0⟩→BS(θ)→|<0,1|ψ>|²（=sin²θ）
```

链：squeeze U → Kerr 对角 → 真空 |0⟩ → ρ = ψψ† → loss 超算符（`np.stack(_kraus_ops(cutoff, T))` numpy 预构建常数，einsum `'kam,mn,kbn->ab'`）→ 与偶猫态 |α⟩+|−α⟩ 保真度。猫振幅 jnp 内联（5 行）：`c_n = e^{−|α|²/2}/√(2(1+e^{−2|α|²})) · (1+(−1)ⁿ)αⁿ/√n!`。

实证（2026-08-12）：全链 jax.grad 首编 2.6s / 缓存 25ms；对账 numpy loss 1.7e-09；grad vs fd（h=1e-5）≈1e-5 — 测试用 h=1e-6 + atol 1e-6（Gaussian 同款）。

### 3. 测试 `tests/test_fock_ad_f4.py`（commit 2）

复用 `tests/conftest.py` 现成 `backend` fixture（numpy + jax-skipif 参数化）：
- 链恒等：`cat_fidelity`/`bs_overlap` 的 numpy vs jax 路径逐元素相等（numpy 路径复用 fock 门真源）
- 梯度 vs 有限差分 ×3（squeeze r / BS θ / Kerr χ，`skipif(not be.HAS_JAX)`，h=1e-6，atol 1e-6）

### 4. notebook `tutorials/07_fock_ad_designer.ipynb`（commit 3，`_build_07.py` 生成）

mirror `tutorials/_build_05.py` 模式（md/code/notebook 辅助 + 路径写入），章节：
1. 物理设定：squeeze(r)+Kerr(χ) 生成近似猫态；loss 破坏非经典性
2. numpy 网格扫描：猫保真度 vs (r, χ)，找合理初值
3. jax.grad vs 有限差分对照（squeeze/BS/Kerr 三参数）
4. 梯度上升优化 (r, χ) → 最优猫保真度；η 扫掠生存曲线（损耗越强，最优压缩越小）
5. 结论：Fock 侧"参数 → 梯度 → 优化"闭环，与 Gaussian 05 对仗

### 5. 不动的东西

- `cvsim/fock/*` 整个包：零改动（ADR-0001 白名单约束，backend 相关只能顶层）
- `FOCK_PUBLIC` 冻结：`cvsim/fock_ad.py` 顶层模块，不进 fock 包 `__all__`（gaussian 侧 ad.py 同样不进）
- `pyproject.toml`：`[jax]` extra 已存在
- `cvsim/backend.py`：已完备（`_get_xp`/`_set`/`_allclose`/`HAS_JAX`），零改动

## 兼容性

- 顶层新模块 `cvsim/fock_ad.py`，对既有代码零改动（fock 包不动，无签名变化）
- 架构测试 `test_architecture.py`：fock_ad 是顶层模块，不在 REP_PACKAGES 扫描范围，无新违规
- numpy 路径复用 fock 包真源公式 → 无公式漂移；jnp 镜像与 numpy 逐元素恒等测试守护

## 风险与回滚

- 高风险点：jnp 镜像与 numpy 门公式漂移 → 恒等测试（backend 参数化）守护；公式出处交叉注释
- `_expm` jnp 路径（jax 0.11 实测 OK）→ 梯度测试已覆盖
- 回滚点：commit 1 独立可回退（纯新增文件，无既有代码改动）
