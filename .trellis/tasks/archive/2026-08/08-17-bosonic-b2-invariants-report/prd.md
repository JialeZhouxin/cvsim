# B2.1 状态不变量与 LeakReport

## Goal

建立 B2 的基础不变量与不可变报告类型：`LeakReport`、`normalize()`、`is_hermitian()`，并完成有限权重和空状态边界测试。

## Requirements

- 在 `cvsim/bosonic/component_eng.py` 定义 `@dataclass(frozen=True) LeakReport`。
- 报告至少包含输入/输出组件数、丢弃组件数、`dropped_weight_mass`、`merge_groups`、`merge_distortion`、`warning`。
- `normalize(state, atol=1e-12) -> BosonicState`：按 `weight_sum = Σw` 缩放权重；零权重和抛 `ValueError`；不改变 `V/rbar`，不修改输入。
- `is_hermitian(state, atol=1e-10, rtol=1e-8) -> bool`：按共轭配对检查 `V/rbar/w`，不自动修复。
- 任意组件权重为 NaN/Inf 时抛 `ValueError`。
- 遵守 `cvsim` 导入边界，不依赖 bridge 或其他表示包。

## Acceptance Criteria

- [ ] LeakReport 是 frozen dataclass，字段默认值能表示无操作报告。
- [ ] normalize 处理实权重、复权重、零和、空状态，且保持函数式。
- [ ] is_hermitian 覆盖实组件自配对、复共轭对、缺失配对、容差边界。
- [ ] 有对应 `tests/test_bosonic_component_eng.py` 单元测试。
- [ ] 现有测试不受影响。
