# B2.4 公共面与回归收口

## Goal

将 B2 能力接入 `cvsim.bosonic` 顶层公共面，完成阶段标记、文档同步和全套回归验证。

## Requirements

- 从 `cvsim.bosonic` 顶层导出 `LeakReport`、`merge`、`truncate`、`normalize`、`is_hermitian`。
- 在 `tests/test_public_api.py` 增加并冻结 `BOSONIC_PUBLIC` 新增项。
- 注册 `phaseB2` pytest marker，并为 B2 测试添加标记。
- 最小同步 `.trellis/spec/cvsim/bosonic.md` 或相关 vision 文档，记录 B2 已落地的边界；不扩展无关 API。
- 运行 B2 专项测试和完整回归；必要时运行 ruff/mypy。

## Acceptance Criteria

- [ ] 顶层导入路径可用，`__all__` 与冻结集合精确匹配。
- [ ] `phaseB2` 在 strict markers 下无警告。
- [ ] B1 专项测试和全套 pytest 通过。
- [ ] 文档与实现/测试契约一致。
- [ ] 记录剩余风险：B3 精确测量尚未实现，组件工程仍为显式调用。
