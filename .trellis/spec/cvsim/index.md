# cvsim Spec Index

`cvsim` 三表示 CV 模拟器（Gaussian / Fock / Bosonic）的**可执行契约**（非物理文档 —— 物理语义以 `docs/vision-*.md` + `docs/adr/` 为唯一事实源）。

| 文件 | 范围 |
|------|------|
| [bosonic.md](./bosonic.md) | Bosonic 表示：模块边界、空态语义、复真空重叠、教学切边界、deprecation 纪律 |

## 跨表示硬约束（agent 必读）

- **物理语义冲突**：vision 文档赢（`docs/vision-*.md`）；改物理先改 vision 再改代码
- **导入边界（ADR-0001）**：rep 包（`cvsim.gaussian/fock/bosonic`）只能 import 根级 `cvsim.conventions` / `cvsim.symplectic` / `cvsim.circuit_common`；**禁止** import `cvsim.bridge`、`cvsim.wigner`、`cvsim.ad`、`cvsim.fock_ad` 及兄弟 rep 包 —— `tests/test_architecture.py` AST 检查强制执行
- **警告即错误**：pyproject `filterwarnings = ["error:cvsim.*"]` —— cvsim 代码发 DeprecationWarning 直接变测试失败；deprecation 只能落 docstring
- **pytest markers**：`--strict-markers`；phase 系列 marker（phaseB1 等）必须先在 `pyproject.toml` `[tool.pytest.ini_options].markers` 注册
- **约定冻结**：xxpp / ħ=1 / √2 位移（api-stability.md §1）；改动 = major + vision amend
