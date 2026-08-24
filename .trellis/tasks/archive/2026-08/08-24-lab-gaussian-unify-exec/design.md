# Design — Lab Gaussian 执行路径统一

## 现状（Before）

```
lab/ir.py _execute(circuit, rng):
  state = vacuum(core.nmode)
  mapping = [0..nmode-1]              # Lab 自维护逻辑→物理映射
  for node in core.ops:
    state, entry = _apply(node, state, mapping, rng)   # 13 分支 dispatch
  return _build_result(state, view, measured)

_apply(node, state, mapping, rng):   # 13 个 if op== 分支
  phys = _logical_phys(mapping, node)  # Lab 自家映射转换
  if op == "squeeze": return squeeze(state, r, phys[0], phi), None
  ... 11 个非测量分支 ...
  if op == "measure_homodyne":
    outcome = homodyne_mean(...) if rng is None else homodyne_sample(...)
    _remove_phys(mapping, ...)          # Lab 自家删模重排
    return st.remove_mode(phys[0]), {op, mode, phi, outcome}
  ...

scan_circuit(circuit, sweep):
  for x in xs:
    rebuild IR with node.param = x      # 每点重建 IR
    st = _state_after(rebuilt_core)     # 又遍历 _apply 跑一遍
    ys.append(log_negativity(st))
```

## 目标（After）

```
lab/ir.py _execute(circuit, rng):
  compiled = GaussianCircuit.from_ir(circuit.raw).compile()   # 一次编译
  state = vacuum(compiled.nmode)
  logical_map = [0..nmode-1]            # 仅记逻辑模号供 entry（不重排）
  for seg in compiled._segments:
    if seg[0] == 'merged':
      state = compiled._apply_merged(ops, nmode, values, state)   # 复用合并执行
    else:  # 断点 op（测量）
      node = IRNode from seg[1]         # op_name, phys_modes, fixed, pnames, refs
      logical_mode = logical_map[...]   # 从原始 IR 取逻辑模号
      state, entry = _apply_measure(op_name, state, phys, logical_mode, fixed, rng)
  return _build_result(state, view, measured)

_apply_measure(op_name, state, phys, logical_mode, fixed, rng):  # 仅 2-3 分支
  if op == "measure_homodyne":
    outcome = homodyne_mean(...) if rng is None else homodyne_sample_and_condition(...)
    return st.remove_mode(phys[0]), {op, mode=logical_mode, phi, outcome}
  if op == "measure_heterodyne": ...
  if op == "measure_threshold": raise CircuitV0Error(...)   # Q6=C 拒绝

scan_circuit(circuit, sweep):
  # 把 sweep param 注成 symbolic $param
  ir = _inject_symbolic_param(circuit.raw, node_id, param)
  compiled = GaussianCircuit.from_ir(ir).compile()   # 一次编译
  for x in xs:
    state, _ = compiled.run(**{param: x})            # 值绑定，不重编译
    ys.append(_safe_logneg(state, modes_A))
```

## 关键设计点

### D1 segment 结构（circuit_common.py L99-101）
断点 op 段 tuple：`('op', (op_name, phys_modes_tuple, fixed_dict, pnames_dict, refs_dict))`
- `phys_modes` 已被 `compile_segments` 转成 physical 坐标（删模后重排完成）
- Lab 直接用 phys_modes 操作状态，不需自家 mapping 重排
- entry 的 `mode` 字段从 IR node 原始 modes 取（逻辑模号，前端展示）

### D2 Lab 逻辑模号追踪
`compile_segments` 把测量 op 段的 modes 转成 physical，但 entry 要逻辑模号。
方案：Lab 遍历 segments 时维护一个 `logical_modes` 列表——对每个断点 op，从 `circuit.core.ops`（IR）按顺序取对应 node 的 `modes[0]`。
或更简：segment 断点 op 段里只存了 physical，但 Lab 仍有 `circuit.core.ops`（IR）原始数据，按断点顺序对齐取逻辑模号。

### D3 scan symbolic param 注入
IR 里 param 值改 `{"$param": "sweep_x"}`，`from_ir` 解析成 symbolic，`compile` 后 `run(sweep_x=x)` 绑定。
`_inject_symbolic_param(raw, node_id, param)`: 深拷贝 raw，找到 node_id 的 node，把 params[param] 替换成 `{"$param": "sweep_x"}`。

### D4 mean path 语义保（Q1=A）
`/run`（rng=None）：测量走 `homodyne_mean` + `homodyne_condition`（确定性期望）。
注意：`homodyne_sample_and_condition(rng=None)` 会 fall back 抽随机——**不能用**。Lab 测量分支显式分 rng is None / not None 两路。

## 删除清单

| 函数 | 行数 | 原因 |
|------|------|------|
| `_apply` 非测量 11 分支 | ~70 | 交 compiled._apply_merged |
| `_logical_phys` | ~10 | compile_segments 已做映射 |
| `_remove_phys` | ~6 | compile_segments 已做重排 |
| `_state_after` | ~10 | 被 compiled.run 替代 |
| scan 每点重建 IR 循环 | ~15 | symbolic param 一次编译 |

## 风险

- **R1**：segment 断点 op 与 IR node 顺序对齐——需验证 `compile_segments` 不重排断点 op。查 circuit_common.py L75-101：断点 op 按 `append` 顺序加入 segments，与原 ops 顺序一致。安全。
- **R2**：scan symbolic param 注入——IR node 的 param 原是裸值，改 `$param` 后 `validate_ir` 需接受。查 ir.py L152-162：`$param` 已是合法值形式。安全。
- **R3**：`_apply_merged` 接受 `values` dict（symbolic param 绑定）——`_execute` 无 symbolic 时传空 dict。
