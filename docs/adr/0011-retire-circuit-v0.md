# ADR-0011: 退役 circuit_v0 读兼容

- 日期: 2026-09-07
- 状态: 已接受
- 取代: ADR-0003 决策 8（"load 接受 v0（翻译）+ v1"）

## 背景

v0 写路径已死（UI 保存唯一出口 `toV1Json` → circuit_v1），但两端各自维护一份
v0 读解析器：

- Python `cvsim/lab/ir.py::translate_v0`（+五张 v0 映射表、`_as_complex` 专用 helper）
- JS `cvsim/lab/static/editor.js::stateFromJson` 的 v0 分支（`Object.hasOwn(OPS, ...)` 路径）

默认场景 `default_scene.js` 仍是 `schema: "circuit_v0"` 字样，UI 侧日常仍走这条
行将被退役的路径——v0 读兼容事实上已无信号。

**前置决策**：用户确认「无存量 v0 文件」。因此选择**全删**，而非半刀保留。

## 决策

1. **删除 `translate_v0` Python 端**：`ir.py` 中的函数、五张映射表（`SOURCE_V0`、
   `V0_TO_V1_OP`、`V0_TO_V1_PARAM`、`SINGLE_MODE_V0`、`TWO_MODE_V0`）、`_as_complex`
   全删。`MEASUREMENT_OPS` 保留（`gaussian_backend.py`/`scan.py` 消费）。
   `load_circuit` schema 校验收紧为仅 `circuit_v1`，错误消息相应收紧。
   `lab/__init__.py` 移除 `translate_v0` 导出（公开 API 收缩）。
2. **删除 JS 端 v0 分支**：`stateFromJson` 收敛为「非 `circuit_v1` →
   `{ error: "schema 必须是 circuit_v1" }`」，直接委托 `stateFromV1`。函数名沿用
   （调用点不动：app.js L387/441/802/817）。
3. **默认场景迁 v1**：`default_scene.js` 的 `DEFAULT_SCENE` 字面量改为
   circuit_v1 形态（`nmode: 2` + 两路 `displace`、`alpha: [1.0, 0.0]`、
   `ui.staff: { d0: 0, d1: 0 }`）。
4. **测试全 v1 化**：删除 `tests/test_ir_translate.py` 整文件；其余测试
   fixture 手改为 v1（无测试侧翻译 helper——那等于把 translate_v0 搬进测试）。
   v0 专属断言（多源直积、source-first 校验、`mode`/`modes` 归一化翻译规则）
   直接删除；schema 语义等价的保护断言（未知 op、proto 注入、id 去重、参数
   极性、seed/backend/initial 扩展）以 v1 形式保留。

## 影响

- 旧 v0 文件**不再可读**，报错 `unsupported schema 'circuit_v0'; expected 'circuit_v1'`。
- 公开 Python API 减 1（`translate_v0` 从 `lab.__all__` 移除）。
- 无功能回归：同样电路在 v1 下沉（UI 只写 v1 已久）。
- 约 −250 行产品代码 / −570 行测试代码退役（合计净约 −460 行，含测试 v1 化的新增断言），噪声按 schema 单点收敛。

## 单向决策说明

这是单向门（one-way door）：一旦任何用户手边存在 v0 存档将无法读回。用户确认无
存量，故接受此代价。若未来发现误删场景，`docs/api-stability.md` 中的 v0 行注明
「已移除（ADR-0011）」；恢复路径 = `git revert` 当前提交，不做半删状态下的双轨。
