# circuit serialize IR 收编

## Goal

把 Lab 探路出的 `circuit_v0` JSON 收编为**核心正式 IR `circuit_v1`**：`GaussianCircuit` 可无损 `to_ir()/from_ir()`；Lab 迁移为纯消费者（直接读写 v1，旧 v0 文件经纯函数翻译）。结构已 grill 收敛（ADR-0003）。

## Requirements

1. **单一正式 IR**（`circuit_v1`）在核心 `cvsim/gaussian/ir.py`，Lab 不再自持格式。
2. **无源概念**：顶层 `nmode`，所有"源"是门/通道特例（coherent≡displace、tmsv≡two_mode_squeeze、thermal≡amplifier(G=1+2nbar)）；执行 = 建真空 → 顺序应用 ops。
3. **全 op 集 1:1** 对齐 `GaussianCircuit` builder（14 op，含 cz/cx/interferometer/phase_noise/gaussian_channel/mach_zehnder），`to_ir`/`from_ir` 往返无损。
4. **参数编码**：扁平命名 `params` dict；值枚举 = number / 复数 `[re,im]` / 矩阵嵌套数组 / `{"$param": name}` 符号参数 / `{"$ref": name, "gain": g}` 前馈；省略参数 = 库默认值（golden 锁定每 op 默认表）。
5. **统一 `modes` 数组**（不分 mode/modes）；数组序 = 执行序；测量删模后逻辑索引重映射（运行时）。
6. **校验分工**：IR 层只做结构校验；物理范围校验留在库函数。
7. **schema 版本化**：破坏性变更走 `circuit_v2`，不静默改语义。
8. **Lab 迁移**：`load` 同时接受 v0（翻译函数 → v1）与 v1；`save` 写 v1；`view/seed/ui` 为顶层扩展字段，核心校验忽略（vision-gaussian-lab-ui §7.5 允许）；其余未知顶层字段拒绝。
9. **`id` 可选**：省略按数组序生成 `n0,n1,…`（错误消息引用）；存在则校验唯一性。核心逻辑不依赖 id。

## Acceptance Criteria

- [ ] `cvsim/gaussian/ir.py`：schema 定义 + 结构校验 + `to_ir()/from_ir()`；`GaussianCircuit.to_ir()` / `GaussianCircuit.from_ir()` 往返等价（`V,rbar` atol=1e-12）。
- [ ] Golden：JSON fixture → run 与手写等价 Python 电路一致（atol 约定）。
- [ ] 旧 `circuit_v0` 文件（含 tmsv/coherent 源、多源、heterodyne/homodyne）翻译到 v1 后运行结果与 v0 引擎一致（golden 测试）。
- [ ] Lab 迁移：后端 `ir.py` 改造为 v1 引擎 + v0 翻译层；save 写 v1；前端零物理改动或最小适配。
- [ ] 全量 pytest 绿 + 既有 Lab UI 测试绿；OCR review 每 commit（high/medium 清零）。
- [ ] vision-gaussian-lab-ui §7/§14 与 simulator vision §10 已修订；ADR-0003 已落盘。

## Notes

- 设计决策全链：Q1–Q8 grill 记录见 ADR-0003；术语进根 CONTEXT.md。
- 拆分触发器（ADR-0001 #5）已触发：`lab/ir.py` 出现 circuit_v1 后按本任务结构拆（核心 ir.py + lab 翻译层），不复用旧布局。
- 核心 IR 不带 seed（rng 由运行环境注入，与 `GaussianCircuit.run(rng=)` 一致）；seed 属 Lab 扩展字段。
