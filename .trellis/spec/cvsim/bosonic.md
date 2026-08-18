# Bosonic 表示 — 可执行契约（B1 落地固化）

> 物理/架构决策事实源：`docs/vision-bosonic-simulator.md` + `docs/adr/0005` + `docs/adr/0006` + 任务 `08-14-bosonic-architecture/design.md`。本文件只记 agent 实施时必须遵守的边界与坑。

## 1. 模块边界与导入

- `cvsim/bosonic/*` 只 import `cvsim.conventions` / `cvsim.symplectic`（+ 包内模块）。**禁 import `cvsim.bridge`**（ADR-0001 ALLOWED_ROOT_IMPORTS 不含它，`test_architecture.py` 会红）。
- 测量在 `cvsim/bosonic/measure.py`（A4）；`observables.py` 只留矩 + `_as_real` 等私有 helper。
- B3 前 homodyne 实现单一来源 = `observables.py`，`measure.py` re-export；外部路径 `cvsim.bosonic.homodyne_*` 冻结不变（BOSONIC_PUBLIC 33 名，`test_public_api.py`）。

## 2. 空态语义

- `BosonicState.nmode`：空 components 返回 `0`（不抛错）—— heterodyne 删模尾部（单模 K=1 条件化后）。
- heterodyne 条件化后的单模多分量态 = **0-dim-V components**（V shape (0,0)，权重保留归一化 Σw=1）；不是空列表。
- `gates._nmode` 对空态**保持抛错**（对空态应用门 = 用户错误）。

## 3. 真空重叠 — bridge 浮点化陷阱（Gotcha）

> **Warning**: `cvsim.bridge.vacuum_probability` 内部 `rbar = np.asarray(rbar, dtype=float)` —— **静默丢弃复位移虚部**（干涉中心）。交叉分量的真空重叠会错。

- Bosonic 阈值测量用私有 `_vacuum_probability_complex`（measure.py）：同一二次型 `e^{−½r̄ᵀ(V+½I)⁻¹r̄}/√det(V+½I)`，复 r̄ 能力；实 r̄ 时与 bridge 数值一致（K=1 测试证明）。
- 复值结果取实部必须过虚部容差检查（`_as_real`，|imag| > 1e-8 抛错）—— 永不许静默丢干涉。

## 4. 教学切边界（B1 → B3）

- heterodyne（B1）= **教学切**：sample/condition 只用实对角分量池（`imag_tol=1e-12` 过滤），K=1 与 Gaussian 严格对齐；混合态精确化（CDF 反演）属 B3，同 homodyne。
- homodyne（B1）= 教学切（`homodyne_sample` 实峰池）→ B3 换 CDF 网格反演（ADR-0006）。
- 教学切 API 的 docstring 必须显式标注"teaching cut, not production"——防被当生产用。

## 5. deprecation 纪律

- pyproject `filterwarnings = ["error:cvsim.*"]`：cvsim 模块发 `DeprecationWarning` → pytest error。**deprecation 只能写 docstring**（`.. deprecated::` 块），零运行时 warning。
- 先例：`gkp_logical_overlap`（B1，指向 B2/B4 `pure_fidelity`）。

## 6. B2 组件工程

- `cvsim.bosonic.component_eng` 提供纯函数 `merge`、`truncate`、`normalize`、`is_hermitian` 与 frozen `LeakReport`。
- `merge` 默认 `atol=1e-10`、`rtol=1e-8`，按输入顺序稳定贪心分组；代表保留组内第一组件，权重求和，畸变写入报告。
- `truncate` 默认只删除 `abs(w) < 1e-6` 的组件；丢弃质量 `sum(abs(w))`，超过 `1e-6` 警告、超过 `1e-3` 失败，`validate=True` 时超过警告阈值即失败。
- 组件工程不自动归一化、不修改输入；推荐显式先 `merge` 后 `truncate`，分别保存报告。
- B2 不改变 B1 门、通道、测量的隐式行为；精确测量仍属 B3。

## 7. 门/通道对齐模式

- 门 = 薄封装 `apply_symplectic(state, S_*(...))`，签名 1:1 复制 `cvsim/gaussian/gates.py`（含 `interferometer(..., *, validate_u=True)`）。
- 通道 = 逐分量 `V_k ← X V_k Xᵀ + Y`，权重不动，V 对称化；X/Y 数学复制 Gaussian channels.py（amplifier `X=√G·I, Y=(G−1)(nbar+½)·I`；phase_noise `X=e^{−σ²/2}·I, Y=(1−e^{−σ²})·½·I`）。
- 任何 K=1 对齐改动必须有 `BosonicState.from_gaussian` 包装态 vs `cvsim.gaussian` 的 atol 测试。

## 7. 验证命令

```powershell
.venv\Scripts\python.exe -m pytest -q                                   # 全套（1059+）
.venv\Scripts\python.exe -m pytest -m phaseB1 -q                        # B1 切片
```
