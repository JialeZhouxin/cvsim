# Phase F1 核心补全（08-11-cvsim-phase-f1）

> 父任务。执行蓝图：`.trellis/tasks/archive/2026-08/08-10-cvsim-fock-arch/design.md` + ADR-0004。

## Goal

Fock 生产级 F1：核心能力补全（工厂/门/通道/泄漏纪律）+ circuit_common 迁移前置。
镜像 vision-fock-simulator.md §4 F1。

## 子任务

| # | 子任务 | 内容 | 验证 |
|---|--------|------|------|
| 1 | `08-11-f1-circuit-common` | circuit_common.py 提取 + 高斯迁移（git mv 语义，无双份逻辑） | 766 全绿 + OCR |
| 2 | f1-factories | coherent/squeezed/cat/thermal 工厂 + 泄漏三件套（解析尾部 golden） | 解析尾部 vs 高 cutoff 对照 atol golden |
| 3 | f1-gates | cz/cx/mach_zehnder/interferometer/apply_unitary（连续变量物理） | 与高斯 S 矩阵对照 atol |
| 4 | f1-channels | amplifier/phase_noise Kraus + apply_kraus 通用入口 | CP/TP 不变式 + 高斯对照 |

## F1 Exit Criteria（vision §4 F1）

1. 核心工厂/门/通道全部 public + docstring 数学式
2. Leakage API 解析尾部 vs 高 cutoff 对照一致（golden）
3. pytest 全绿；无约定漂移

## 全局约束（架构已锁）

- 标量 cutoff（per-mode F2/F3）
- 泄漏三件套：`truncation_leakage -> float|None` / `check_leakage` / `estimate_leakage`
- CZ/CX = 连续变量物理 e^{i g x̂⊗x̂}（与高斯同约定）
- thermal 归 FockDensity
- api-freeze 在 F2 出口，F1 导出面自由生长
