# ADR-0001: cvsim 模块边界契约

- 日期: 2026-08-08
- 状态: 已接受

## 背景

cvsim 是教学用的三表示模拟器（Gaussian / Fock / Bosonic），约 4.6K 行。
Phase 3 会继续扩展。审问（grill-with-docs）确认：模块化问题不是"文件不够多"，
而是边界是否被**明确写成契约**。当时现状：依赖方向已自然单向（lab → gaussian +
wigner，表示包互不 import），但只是"巧合合规"，无测试兜底、无文档声明。

## 决策

1. **表示包互不 import**。`cvsim.gaussian` / `cvsim.fock` / `cvsim.bosonic`
   之间禁止任何 import；跨表示的共享代码只允许放根级
   （`cvsim.conventions`、`cvsim.symplectic`、`cvsim.wigner` 这类）。
2. **表示包只允许 import 根级 allowlist**：`cvsim.conventions`、
   `cvsim.symplectic`。不得 import `cvsim.wigner` / `cvsim.lab` /
   `cvsim.demos` 及表示包互引。
3. **分析实现按表示私有**。分析概念（purity、entropy、fidelity 等）跨表示共享
   **名字**，算法按表示不同（gaussian 走 symplectic 谱，fock 走 tr(ρ²)，
   bosonic 走分量加权）。`gaussian/analyse.py` 不上提根级；fock/bosonic
   需要时在各自包内实现同名函数，不得 import `gaussian.analyse`。
4. **公开 API = `__init__.py` 的 `__all__` 白名单**。四个 `__init__.py`
   均已显式再导出；未列入白名单的符号视为私有。
5. **大文件不拆，立触发器**。`lab/ir.py`（499 行，schema + 执行两层）保持
   单文件 + 分区注释；文件超 ~800 行或出现 circuit_v1 schema 时再拆。
6. **契约由测试强制**：`tests/test_architecture.py` 用标准库 `ast`
   解析源码断言 1–2，零新增依赖。

## 权衡

- 曾考虑把 `analyse` 上提为根级共享分析层：被否。上提会造一个"假共享层"，
  内部全是 V/r̄ 形状假设，fock/bosonic 用不上，且违反"根级=真共享"语义。
- 曾考虑拆 `lab/ir.py`：被否。schema 与执行层强耦合（schema 加 op 执行层
  必须同步改），拆开反而制造同步风险；真正的模块化是边界清晰，不是文件多。
- 曾考虑引入 import-linter 依赖：被否。40 行 AST 测试即可覆盖，教学库
  不引重型工具。

## 后果

- 表示包新增根级依赖时，需同时改本 ADR + `test_architecture.py` allowlist。
- 测试在 CI/本地套件中第一时间爆红，腐化不可静默。
