# Implement — 执行顺序与验证

## Phase 1: 验证前置假设

- [ ] 确认 `compile_segments` 断点 op 顺序 = 原 ops 顺序（查 circuit_common.py L75-101）
- [ ] 确认 segment 断点 op tuple 结构 `('op', (op_name, phys_modes, fixed, pnames, refs))`
- [ ] 确认 `compiled._apply_merged(ops, nmode, values, st)` 签名（gaussian/compile.py L193）
- [ ] 确认 IR `$param` 注入后 `validate_ir` 接受（ir.py L152）
- [ ] 跑基线 pytest 确认 1147 绿

## Phase 2: 重构 `_execute` + `_apply`

1. 新增 `_apply_measure(op_name, state, phys, logical_mode, fixed, *, rng)` —— 仅 homodyne/heterodyne/threshold 三分支
2. 重写 `_execute(circuit, *, rng)`：
   - `compiled = GaussianCircuit.from_ir(circuit.raw).compile()`
   - 遍历 `compiled._segments`：merged → `_apply_merged`；op 段 → `_apply_measure`
   - 维护 `logical_modes` 对齐 IR node 取逻辑模号
3. 删旧 `_apply`（13 分支）、`_logical_phys`、`_remove_phys`
4. `_build_result` / `_meters` 不动

验证：`py -3 -m pytest tests/test_lab_ir.py tests/test_lab_l3.py tests/test_ir_translate.py -x`

## Phase 3: 重构 `scan_circuit` + 删 `_state_after`

1. 新增 `_inject_symbolic_param(raw, node_id, param)` —— 深拷贝 raw，替换 param 为 `{"$param": "sweep_x"}`
2. 重写 `scan_circuit`：
   - 注入 symbolic → `from_ir` → `compile` 一次
   - 每点 `compiled.run(**{"sweep_x": x})` → `_safe_logneg`
3. 删 `_state_after`
4. 保持 `/scan` 契约（scan-api.md）：请求/响应格式不变，纯函数无 RNG

验证：`py -3 -m pytest tests/test_lab_scan.py tests/test_lab_api.py -x`（若存在）

## Phase 4: 全量回归

- [ ] `py -3 -m pytest -x` 全绿
- [ ] `py -3 -m pytest --tb=short 2>&1 | tail -5` 确认 1147 passed
- [ ] `wc -l cvsim/lab/ir.py` 确认体积下降
- [ ] grep 确认 `_apply`/`_logical_phys`/`_remove_phys`/`_state_after` 已删

## Phase 5: 浏览器探针（Lab UI）

- 启 Lab server，跑 Gaussian 电路 `/run` + `/sample` + `/scan`
- 确认前端 measured 面板、wigner、meters 正常
- 确认 `/run` 确定性、`/sample` 抽样、`/scan` 曲线

## 不做

- 不动 Fock/Bosonic 路径
- 不动 `_meters`/`_build_result`
- 不动结果组装胶水
- 不动 circuit_common / gaussian/compile / gaussian/circuit
- 不改公开 API（`__all__` 不变）
