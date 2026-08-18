# B2.3 组件截断与泄漏纪律

## Goal

实现显式 `amp_cutoff` 截断和与 Fock 对齐的泄漏阈值纪律。

## Requirements

- 在 `cvsim/bosonic/component_eng.py` 实现 `truncate(state, *, amp_cutoff=1e-6, validate=False, warn_threshold=1e-6, fail_threshold=1e-3) -> (BosonicState, LeakReport)`。
- 仅删除 `abs(w) < amp_cutoff` 的组件，恰好等于阈值时保留。
- 默认先检查所有权重有限性；`amp_cutoff` 与阈值必须非负且有限。
- `dropped_weight_mass = Σ|w|`，仅作为丢弃预算，不作为归一化判据。
- 丢弃质量超过 `fail_threshold` 抛 `ValueError`；`validate=True` 且超过 `warn_threshold` 也抛；否则超过警告阈值发 `RuntimeWarning`。
- 全量截断在不触发失败纪律时返回空 `BosonicState` 与报告，不补真空。
- 不自动归一化、不修改输入。

## Acceptance Criteria

- [ ] 小权重、边界权重、amp_cutoff=0 均有测试。
- [ ] 警告、严格模式、硬失败阈值与 Fock 行为一致。
- [ ] 全量截断的空状态与超失败阈值的异常行为均有测试。
- [ ] NaN/Inf 权重、非法阈值均有测试。
- [ ] 截断报告组件数与丢弃预算准确。
