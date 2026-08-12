# PRD — Phase F4: Fock differentiable designer (backend= + AD)

## Goal

Vision §4 F4（`docs/vision-fock-simulator.md` F4 节）：Fock 侧"参数 → 梯度 → 优化"闭环 — 可微链
（squeeze/BS/Kerr 梯度，jax.grad 可穿）+ numpy/jax 共享测试 + 一个优化 notebook，
与 Gaussian Phase 4（`cvsim/ad.py` + `tutorials/05_ad_designer.ipynb`）对等。

## Vision 原文要求（F4 退出判据）

1. Gradients agree with finite difference (squeeze/BS/Kerr) — mirror Gaussian Phase 4 bar (2e-07).
2. Numpy and JAX paths share tests via backend parametrization.

## Background（已确认事实，2026-08-12）

- **ADR-0001 硬约束**：`test_architecture.py` AST 扫描 — rep 包 `cvsim.fock` 只允许 import
  `conventions/symplectic/circuit_common`；`cvsim.backend` 不在白名单 → backend 相关模块必须**顶层**。
  Gaussian 先例同构：`gaussian/gates.py` 零 backend 命中，backend 化在顶层 `symplectic.py`（矩阵级）+ `cvsim/ad.py`（链）。
- `cvsim/backend.py` 已完备：`_get_xp`/`_set`/`_allclose`/`HAS_JAX`/`BACKENDS`，jax x64 强制内置。
- jax 0.11.0 本地已装；`jax.scipy.linalg.expm` 可微已验证（squeeze U(0.3) grad 正常；BS |1,0⟩ 梯度 0.717356 vs 解析 2sinθcosθ=0.7174）。
- **loss 通道 jax 兼容已验证**：`_kraus_ops` 仅依赖 (N, T)，numpy 预构建 → 常数张量 + jnp einsum
  `'kam,mn,kbn->ab'`；对账 numpy loss 1.7e-09；全链 jax.grad 首编 2.6s、缓存 25ms。
  jax 内重建 Kraus 不可行（vmap+arange 撞 ConcretizationError，已实证）。
- `FockState.__post_init__` 强制 `np.asarray(dtype=complex)` → jax 数组不进 state；可微链用裸 jnp（不建 FockState）。
- `FockState.cat()` 工厂已有（numpy）；猫振幅 jnp 内联 5 行。
- `tests/conftest.py` 已有 `backend` fixture（numpy + jax-skipif）；Gaussian 梯度测试模板：h=1e-6、atol 1e-6。
- `tests/test_public_api.py` FOCK_PUBLIC 冻结 35 导出（fock 包零改动则冻结零改动）。
- Fock 测试面 193 passed；tutorials 编号到 06 → 新 notebook = 07。

## Requirements

- R1: 新建**顶层** `cvsim/fock_ad.py`（镜像 `cvsim/ad.py` 结构：`backend:` 首参、`_get_xp` 分发、交叉注释）：
  `squeeze_u` / `bs_u` / `kerr_diag`（numpy 路径复用 `cvsim.fock.gates` 真源公式；jax 路径 jnp 镜像）+ 全链
  `cat_fidelity(backend, r, chi, *, alpha, T=1.0, cutoff=12)`（squeeze→Kerr→|0⟩→ρ→loss→猫态保真度）+ `bs_overlap`（BS 梯度测试链）。
- R2: `cvsim/fock/*` **零改动**（ADR-0001）；FOCK_PUBLIC 冻结零改动（fock_ad 不进 `__all__`，mirror gaussian ad.py）。
- R3: 测试 `tests/test_fock_ad_f4.py`：numpy/jax 路径恒等（conftest `backend` fixture 参数化）+ 梯度 vs fd ×3
  （squeeze r / BS θ / Kerr χ，`skipif(not be.HAS_JAX)`，h=1e-6，atol 1e-6 — Gaussian bar）；jax 未装时全 skip、numpy 仍绿。
- R4: 优化 notebook `tutorials/07_fock_ad_designer.ipynb`（`_build_07.py` 生成，mirror `_build_05.py`）：
  ① 物理设定（Kerr-squeezed 生成近似猫态 + loss 破坏非经典性）② numpy 网格扫描找初值 ③ jax.grad vs fd 对照
  ④ 梯度上升优化 (r, χ) + η 扫掠生存曲线 ⑤ 结论（与 Gaussian 05 对仗）。纯公共 API（禁用 dq/DeepQuantum 教学约束）。
- R5: jax 为 optional（`[jax]` extra 已存在，确认）；核心 import 路径不触碰 jax。
- R6: 现有 193 Fock 测试保持绿；`test_architecture.py` 无新违规。

## Acceptance Criteria

- [ ] `squeeze_u`/`bs_u`/`kerr_diag` 的 numpy 路径与 `cvsim.fock.gates` 公式逐位一致（真源复用，无漂移）
- [ ] `cat_fidelity`/`bs_overlap` numpy vs jax 路径逐元素相等（backend 参数化共享测试）
- [ ] jax.grad vs 有限差分一致 ×3（squeeze/BS/Kerr），bar = Gaussian 同款（h=1e-6，atol 1e-6）
- [ ] jax 未装环境：jax 测试全 skip，numpy 路径全绿（CI 无 `[jax]` 可跑）
- [ ] `pytest -k fock` 全绿（193 + 新增）；`test_public_api.py` / `test_architecture.py` 零改动绿
- [ ] notebook 07 生成 + Run-All 通过；内容覆盖梯度对照 + 优化收敛 + η 生存曲线

## Out of scope

- Torch 后端（Gaussian 侧也没做）；F5（bridge 正式 API）；F6（SF interop）
- Fock 门/FockState 层 backend 化（ADR-0001 禁止 rep 包触碰 backend；可微核只在顶层链层）
- 密度矩阵可微目标（sqrtm 无 jax 对应；纯态保真度足够教学）
- 稀疏/多模（m>2）AD；Kraus 的 jax 内重建（已实证不可行，用 numpy 常数张量）

## Resolved decisions

- **Q1（backend 落点）**: 顶层 `cvsim/fock_ad.py`（ADR-0001 强制；镜像 Gaussian `symplectic.py`+`ad.py` 模式）。
  numpy 路径复用 fock 包真源公式（无重复实现）；jnp 镜像与 numpy 恒等测试守护。
- **Q2（jax 数组与 FockState 冲突）**: 可微链用裸 jnp 数组，不建 FockState（`__post_init__` 强制 numpy，维持现状）。
- **Q3（expm 分发）**: numpy → `scipy.linalg.expm`（复用 fock 门现有路径）；jax → `jax.scipy.linalg.expm`。
- **Q4（notebook 目标）**: squeeze(r)+Kerr(χ) → loss(η) → 与偶猫态 |α⟩+|−α⟩ 保真度最大化（用户拍板；
  loss 用 numpy 预构建 Kraus 常数 + einsum，对账 1.7e-09，首编 2.6s）。notebook 编号 07。
- **Q5（任务粒度）**: 单任务、3 commit（用户拍板：① fock_ad.py ② 测试 ③ notebook）；不拆 children。
