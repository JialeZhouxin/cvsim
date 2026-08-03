# PRD — Gaussian Lab L0: `circuit_v0` IR + `/run` backend

> 来源: [`docs/vision-gaussian-lab-ui.md`](../../docs/vision-gaussian-lab-ui.md) §5/§6/§7/§8/§11/§12
> 状态: **planning**（2026-08-03）
> 物理/API SoT: `docs/vision-gaussian-simulator.md` + `docs/api-stability.md` — 冲突时后者胜

## 1. 背景

Lab UI vision 已锁定（commit `80f5c3a`）。Phase 1–2 模拟器能力已齐（GaussianState、gates、channels、analyse、heterodyne、wigner_grid）。L0 是 Lab 第一条实现切片：**先立 IR 与后端，后做皮**（vision §11: 不可先做漂亮壳后接物理）。

## 2. 目标（L0 三件套）

| Feature ID | Deliverable | Exit |
|-----------|-------------|------|
| **F-LAB-IR** | `circuit_v0` schema：定义、验证、编译到 `GaussianCircuit` | A9 雏形: golden JSON fixture → 手写等价 Python 电路的 `V,rbar` 一致 (atol) |
| **F-LAB-API** | 本地 FastAPI 薄后端 `POST /run` + `GET /health` | A8: 后端 grep 无 `cvsim.gaussian._` private import |
| **F-LAB-WIGNER** | `/run` 返回 view 模式: ptrace + `wigner_grid` payload + meters | A4 雏形: Wigner(vacuum) 与 `wigner_grid` 直调一致 |

## 3. 范围

**做**:
- `circuit_v0` JSON schema（节点白名单见 §4）+ 校验 + 拓扑→`GaussianCircuit` 编译
- `POST /run`：body = circuit_v0 (+ view) → `nmode, rbar, V`（摘要）、`wigner: {x,p,W}`、`meters`（purity / mean_photon / log_negativity）
- `GET /health`：版本 + cvsim 可 import
- golden 等价性测试（JSON ↔ 手写 Python 电路）
- FastAPI/Starlette + uvicorn 依赖（pyproject 新增）

**不做**（L1–L4 / 明确砍项）:
- 拖拽编辑器、任何前端（L2）
- Save/Load、Measure once、seed（L3）— `/sample` 端点**不建**，vision §8 允许合并到 L3 再做
- 扫参、undo、非白名单 op、Fock/Bosonic、`ui` 字段参与物理

## 4. `circuit_v0` 白名单（vision §4 完整 v0 白名单）

L0 即冻结完整 v0 白名单；其余 op 验证时拒绝（`HTTP 422` 带原因）。超白名单 = 先 amend vision §4。

| 类别 | op | params | 编译映射 |
|------|----|--------|---------|
| Source | `vacuum` | `nmode`(默认 1) | `GaussianState.vacuum` |
| Source | `coherent` | `alpha`(complex) | `GaussianState.coherent` |
| Source | `tmsv` | `r` | `GaussianState.tmsv` |
| Gate | `displace` | `alpha` | `displace` |
| Gate | `phase` | `phi` | `phase` |
| Gate | `squeeze` | `r, phi`(默认 0) | `squeeze` |
| Gate | `fourier` | — | `fourier` |
| Gate | `beamsplitter` | `theta` | `beamsplitter` |
| Gate | `two_mode_squeeze` | `r, phi`(默认 0) | `two_mode_squeeze` |
| Channel | `loss` | `T, nbar`(默认 0) | `loss` |
| Measure | `homodyne` | `angle`(默认 0)，测后删模语义对齐模拟器电路 | `homodyne_condition` 系 |
| Measure | `heterodyne` | —，测后**移除**被测模 | `heterodyne_condition` |

> Source 节点必须出现在 mode 0 起始；多源/拼接（`product` 节点）defer，不在 v0。

## 5. 设计约束（vision §7，硬性）

1. 版本字段 `"schema": "circuit_v0"`
2. 节点: `id, op, params`, 可选 `modes`/`mode`；模号**显式**写进 JSON，禁止隐式全局模号
3. 与 `GaussianCircuit` 映射**可测试**: JSON → run → 与手写等价 Python state 的 `V,rbar` 一致（atol 约定）
4. `ui` 子树后端**忽略**，不参与编译
5. 破坏性 schema 变更 → `circuit_v1`，不静默改语义
6. 后端 import 白名单（vision §6.2 硬约束）:
   - ✅ `cvsim.gaussian` public `__all__`、`cvsim.wigner.wigner_grid`、`cvsim.conventions` 只读常量
   - ❌ 任何 `_*` private、复制 analyse/symplectic 公式、Fock/Bosonic 调用

## 6. 后端行为

- `POST /run` body: `{"schema": "circuit_v0", "nodes": [...], "edges": [...], "view": {"wigner_mode": 0, "lim": 5.0, "n": 64}, "ui": {}}`
- 响应: `{nmode, rbar, V, wigner: {x, p, W}, meters: {purity, mean_photon, log_negativity(2模时)}, measured: [...]}`
- view 校验: `wigner_mode` 必须 < 最终模数（heterodyne 后少模仍有效）
- 错误: 非法 op / 越界 mode / 物理非法 params → 明确错误信息
- Wigner 网格: `cvsim.wigner.wigner_grid(state_after_ptrace, lim, n)`，N=64 默认
- 性能: m≤4 全跑 ≤200ms local（vision §9）；不做增量缓存

## 7. 验收（L0 Done 判定）

1. **A9 雏形**: golden JSON fixture（TMSV r=0.6 + loss T=0.8 + BS θ=π/4）→ `/run` 返回的 `V,rbar` == 手写 `cvsim.gaussian` 脚本电路 (atol 1e-10)
2. **A4 雏形**: vacuum → Wigner 中心峰值 == `wigner_grid(GaussianState.vacuum(1))` 直调 (atol 1e-10)
3. **A8**: 后端源文件 grep 无 `_` private import；无 Fock/Bosonic import
4. 单测: schema 验证（合法/非法 fixture 表）、编译等价、`/run` 端到端（TestClient）、heterodyne 少模 + Wigner 模号重映射
5. 全套 `pytest` 通过（新增测试并入现有套件）

## 8. 依赖

- `fastapi` + `uvicorn`（新增 dev/runtime 依赖，uv add）
- 测试: `fastapi.testclient`（需 `httpx`）
- 其余复用现有: numpy/scipy/pytest

## 9. 里程碑

1. F-LAB-IR: schema + 验证 + 编译 + golden 等价测试 → verify: pytest 绿
2. F-LAB-API + F-LAB-WIGNER: FastAPI app + `/run` + `/health` → verify: TestClient 端到端 + A8 grep
3. 收尾: vision changelog 更新、任务 archive
