# Spec: Lab 统一结果规约（候选 3 · payload 组装统一）

> 来源：`/improve-codebase-architecture` 审查（2026-09-03，architecture-review-20260903-162552.html 候选 3）+ `/grill-with-docs` 两轮 10 问拷问（2026-09-04）。
> 术语见根 `CONTEXT.md`：**Lab 结果快照 (LabResult)**、**meter 支持矩阵 (meter support matrix)**。
> 架构词汇（module / interface / depth / seam / leverage / locality）按 codebase-design；决策记录见 ADR-0008。

## 问题（审查 + 代码核实的事实）

三后端 payload 组装**双规约**，知识镜像漂移：

1. gaussian 走 `run_circuit/sample_circuit` → `RunResult` dataclass → `server._payload` 再转 dict；fock（`run_fock_circuit`）与 bosonic（`run_bosonic_circuit`）各自手造 payload dict
2. wigner 切片 `{"x": w[0][0].tolist(), "p": w[1][:,0].tolist(), "W": w[2].tolist()}` 重复 **4 处**：`server.py:78`、`fock_backend.py:182`、`bosonic_backend.py:109`、`bosonic_backend.py:141`（steps 路径）
3. meter 键集三套不一致：gaussian = `purity/mean_photon/mean_photon_per_mode/log_negativity/singular`；fock = `…/leakage`；bosonic = 纯核心三键。差异是物理事实，但**无声明处**，前端靠各自硬编码兜底（logneg 缺失显示 "—"）
4. bosonic 跨包 import fock 私有 `_fock_measured`（`bosonic_backend.py:24`）——对称性破口；该函数实际表示无关（只遍历 raw ops + results 字典 + complex/np JSON 转换），命名与归属皆错
5. gaussian payload **缺 `backend` 键**，前端靠"键缺席"隐式分派 gaussian 面板（`app.js:261` 起 if 链）
6. `/sample` 中 fock/bosonic 两分支重复一模一样的 `payload["seed"]=…; payload["sampled"]=True` 两行

**消费者核实**：`RunResult` 仅 `gaussian_backend` + `server._payload` + `test_lab_backend_symmetry.py` 消费；examples/benchmarks/tools/tutorials 零消费。`lab.__all__` 冻结 11 名有结构守卫。`docs/api-stability.md` 只锁定核心三包，不覆盖 `cvsim.lab`。

## 已锁定的设计决策（10 问）

| Q | 决策 |
|---|------|
| Q1.a | **完全统一**：新立 `LabResult` dataclass，三后端都返回它，**一个**序列化器出 dict。拒绝 (c) 往 RunResult 加可选字段——rbar/V 对 fock 无意义、cutoffs/joint 对 gaussian 无意义，会变成满是 None 的杂物袋 |
| Q2.a | **meter 支持矩阵**：公共核心键（purity/mean_photon/mean_photon_per_mode）+ 表示扩展键（gaussian: log_negativity/singular；fock: leakage）作为**声明**，不拉齐键集。物理差异保持诚实，永不 fabricated None。统一的价值在声明处单点，不在键集一致 |
| Q3 | `_fock_measured` **提升为共享公共函数**（改名去掉 fock 前缀），消灭 fock→bosonic 私有破口 |
| Q4 | gaussian **补 `backend: "gaussian"` 键**（LabResult 公共核心必填，自报家门）；加性破坏，测试同步 |
| Q5 | **范围排除曲线形端点**：`/scan`、`/fidelity`（xs/ys 曲线，单生产者无镜像）不纳入。`/batch` 直方图（counts）同为单生产者形状，也不纳入 LabResult 契约 |
| R1 | **落点**：新建 `cvsim/lab/result.py`，依赖图最底层（只 import numpy），ir.py / 三 backend / server 均可安全 import，零环。ir.py 刚被 08-25 票瘦身，不再装响应契约 |
| R2 | **契约**：字段**构造时即 JSON-ready**（wigner 已切片 list、rbar/V 已 tolist、measured 已纯 Python）——存在的 LabResult 不可能不可序列化，`serialize(result, seed, sampled)` 退化成哑装配。`wigner_slice`、`measured_from_results`（原 `_fock_measured`）是它的私有函数 |
| R3 | **server 形态**：endpoint 内 if-分派保留（短且可读），`_payload` 删除，每 endpoint 统一一次 `serialize`；`/sample` 重复两行收敛进 serialize 参数 |
| R4 | **RunResult 删除**：`gaussian_backend._build_result` 直接产 LabResult（rbar/V/wigner/meters 逐字搬运）；`RunResult` 从 ir.py 与 `lab.__all__` 移除，`LabResult` 补位（`__all__` 仍 11 名）；`run_circuit`/`sample_circuit` 公开动词保留，返回类型置换，JSON 字节不变（除 Q4 新增 backend 键） |
| R5 | **矩阵声明位置**：住 `result.py`（响应侧知识不进 schema.py——那是请求侧组装层）；`schema.py` 组装 `/schema` 时引用嵌入。结构守卫：各 backend meters 键集 ⊆ 矩阵声明 |
| R6 | **前端范围**：本票只做后端。矩阵进 `/schema` 但前端暂不消费（现有缺键兜底已正确）；UI 按矩阵渲染 meter 行 = 后续独立小票 |
| R7 | **测试双轴**：(a) golden 回归——重构前抓三 backend × run/sample（+batch）代表性电路当前响应存 golden JSON，重构后逐字节断言（扣除 gaussian 新增 backend 键）；(b) 结构守卫——扩展 `test_lab_backend_symmetry.py`：三 runner 返回 LabResult、backend 模块无手造 payload dict、meters ⊆ 矩阵、wigner 切片全仓仅 result.py 一处（防再漂移）。沿用 08-25 票验证过的模式 |
| R8 | **流程**：**单票**原子替换（拆票只能拆出"加 LabResult 但不切换"的半成品双轨，正是 schema 票刚拆掉的双写反模式）。记录 = 本 spec + ADR-0008「Lab 统一结果规约」（难逆转 ×3 条件满足）。拷问结束后 `/implement` 开新会话从本票驱动 |

## 实施要点（票的工作分解）

1. **Phase 0 · golden**：抓取 gaussian/fock/bosonic × /run、/sample（fock 另加 /batch 两种分支）响应 → `tests/golden/` JSON
2. **Phase 1 · result.py**：`LabResult`（JSON-ready 构造）+ `serialize` + `wigner_slice` + `measured_from_results` + meter 支持矩阵声明 + 键集 ⊆ 矩阵守卫
3. **Phase 2 · 三后端切换**：gaussian_backend `_build_result`→产 LabResult（RunResult 逐字搬运）；fock/bosonic 手造 dict → LabResult（steps 路径用 result.py 的 wigner 装配）；bosonic 改 import 共享 `measured_from_results`
4. **Phase 3 · server**：删 `_payload`，endpoint 收敛 `serialize`；`/schema` 嵌入矩阵
5. **Phase 4 · 清理与守卫**：`RunResult` 移出 ir.py + `lab.__all__`（EXPECTED_ALL 同步）；扩展对称性测试；golden 逐字节断言通过

**验收**：golden 全绿（除声明的加性差异）+ 全量 pytest 绿 + node --test 绿（前端零改动仍兼容）+ wigner 切片全仓 grep 仅 result.py 命中。