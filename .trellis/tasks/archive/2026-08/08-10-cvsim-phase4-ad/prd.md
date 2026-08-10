# PRD — Phase 4: Differentiable designer (F-AD)

## Goal

Vision §4.2 **F-AD**（`docs/vision-gaussian-simulator.md` L550-556, L650-659）：给 cvsim 加可微后端（JAX 优先），参数（squeeze/BS 等）可求梯度，配一个优化 notebook。教学目的：展示"参数 → 梯度 → 优化"闭环。

## Vision 原文要求

- Math identical to numpy path.
- Backend protocol: `Array` type alias; `symplectic` functions backend-agnostic.
- JAX first candidate; Torch second.
- No AD in core import path (optional package extra).
- Phase 4 build: F-AD extras + one optimization notebook (e.g. maximize log-neg under loss).

## Exit criteria（vision §5 Phase 4）

1. Gradients agree with finite difference on squeeze/BS params.
2. Numpy and JAX paths share tests via backend parametrization.

## Confirmed facts（代码库证据）

- 门矩阵唯一来源：`cvsim/symplectic.py`（纯 numpy；`S_squeeze`/`S_beamsplitter`/`S_two_mode_squeeze`/`S_CZ`/`S_CX`/`S_phase`/`S_mach_zehnder`/`d_displace`/`S_from_unitary` 等），spec 规定新门矩阵先落此处。
- 当前**无任何 backend 抽象层**；GaussianState (V, r̄) 为 numpy 数组；apply 链 = S V Sᵀ（xxpp 约定，Ω 在 `cvsim/conventions.py`）。
- `GaussianCircuit` 已有 `ParamRef` + `compile.py` 参数绑定（L2/L4），与本次优化参数无直接依赖。
- JAX / Torch 均未安装；pyproject 已有 optional extras 先例（`[gbs]`、`[lab]`、`[dev]`）。
- 测试 592 全绿（Phase 3 关闭，vision v0.2.0）。
- `log_negativity` 已在 `cvsim/gaussian/analyse.py`（Phase 2，`d53af23`），PT + symplectic 谱，numpy 实现。
- 本仓库理念：最小依赖、教学优先、诚实标注（"not prod"）。

## Requirements

- R1: `cvsim/symplectic.py` 全部 19 个函数 backend 化（`*, backend="numpy"` 默认参数）；16 个函数 np/jnp 双实现，3 个 decompose 函数仅 numpy（jax → NotImplementedError）。
- R2: numpy 与 JAX 路径共享测试（backend 参数化）；JAX 未安装时 skip。
- R3: 梯度 vs 有限差分一致（squeeze/BS 参数）。
- R4: 优化 notebook：TMSV → 损耗 η → 最大化 log-neg E_N，求最优 squeezing r(η)。
- R5: JAX 为 optional extra（`[jax]`），lazy import，不污染核心 import 路径；x64 强制。
- R6: 现有调用方零改动（默认参数向后兼容），592 测试保持绿。
- R7: backend 分发集中在 `cvsim/backend.py`（唯一 JAX 感知点）。

## Out of scope

- Torch 后端（vision 说 second candidate；本次不做）。
- F-BRIDGE（Phase 5）。
- GPU 批处理、approx GBS 等 P2。
- GaussianState dataclass 双后端化（JAX 路径用裸 jnp 数组）。

## Resolved decisions

- **Q1 (2026-08-10): 方案 B** — `cvsim/symplectic.py` 全部 19 个函数 backend 化（`backend="numpy"` 默认参数），不重写为薄 AD 层。范围约束：现有调用方（gates/state/compile/bosonic/wigner）**零改动**，靠默认参数向后兼容；592 测试回归面 = 0。
- **Q2 (2026-08-10): 方案 1** — backend 以每个函数关键字参数 `*, backend="numpy"` 暴露，无全局状态，测试参数化自然。
- **Q3 (2026-08-10): 任务拆分** — parent + 6 children 小步跑（protocol / gates-basic / gates-advanced / validate / decompose / objective-notebook），每步一个 commit，测试先行。
- **Q4 (2026-08-10): 方案 1** — `reck_decomposition` / `clements_decomposition` / `compose_unitary_mesh` 统一接口但仅 numpy（`backend="jax"` 时 `raise NotImplementedError`，docstring 标注；ponytail 注释留升级路径）。其余 16 个函数全量双实现。
- **Q5 (2026-08-10): 方案 1** — notebook 目标：TMSV → 损耗通道 η → 最大化 log-neg E_N，求最优 squeezing r(η)；教学点：纠缠随损耗的生存曲线 + 反向设计；与 exit 1（squeeze 梯度）直接呼应。
- **Q6 (2026-08-10): `[jax]` extra** — 沿用 `[gbs]`/`[lab]` 先例；内容 `jax>=0.4` + `jaxlib`（CPU 即可）。

## Open questions

无（blocking 决策已全部收敛）。
