# Fock 生产级架构设计（08-10-cvsim-fock-arch）

## Goal

产出 Fock 生产级模拟器的**架构设计文档**（定稿后落 `docs/adr/` + 任务 design.md），
为 F1–F6 实现提供骨架。本任务只设计不实现。

## 背景事实（仓库查证）

- `GaussianCircuit`（383 行）：`_ops` 5 元组 `(op_name, modes, fixed, params, refs)` + `_partition` + ParamRef + 组合/序列化骨架
- `compile.py`（374 行）：`_compile_segments`（静态分段 + mode mapping 模拟）+ `CompiledGaussian.run` + `_DISPATCH` 执行表
- ADR-0001（backend-interface.md）：`cvsim.gaussian/fock/bosonic` 只能 import `conventions` + `symplectic`（`tests/test_architecture.py` AST 强制）
- Fock 愿景 Q5：共享电路框架（YAGNI 反转）；Q7：截断泄漏纪律；Q8：双后端；Q6：稠密 m≤4 / 稀疏 m≤10+
- 回归安全网：766 测试（高斯 758 + Fock 8）

## 设计决策点（逐一向用户确认）

| # | 决策 | 状态 |
|---|------|------|
| D1 共享层形态 | 模板方法+注册表 vs 纯函数工具库 vs 继承 | 待问 |
| D2 共享层落点 | `cvsim/circuit_common/`（ADR-0001 修订）vs 单文件 | 待问 |
| D3 高斯迁移策略 | 立即迁移（git mv 语义，766 兜底）vs 复制双份 | 待问 |
| D4 泄漏检查 hook | 位置/频率/默认实现 | 待问 |
| D5 编译抽象 | segments 骨架通用 + 每表示 factor/dispatch 表；Fock 合并策略留 F3 | 待问 |
| D6 设计深度 | 只定骨架（电路层+包布局+泄漏 hook+ADR-0001 修订），稀疏/双后端/IR 细节留各自 phase | 待问 |

## Deliverables

- [ ] 任务 `design.md`：架构设计全文
- [ ] `docs/adr/0004-*.md`：共享电路框架 ADR（难逆转决策）
- [ ] ADR-0001 修订草案（allowlist 加共享层）
- [ ] 用户 review 定稿

## Acceptance Criteria

- [ ] 设计覆盖 D1–D6 全部拍板项
- [ ] 高斯回归路径明确（迁移步骤 + 766 测试验证命令）
- [ ] 用户审阅通过
