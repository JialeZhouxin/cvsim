# F-COMPILE 实施计划

PRD: prd.md · 设计: design.md · 决策: docs/adr/0002

## 步骤

1. **`cvsim/gaussian/compile.py` 新建** — 段切分（静态 mapping 模拟 +
   断点规则）、`CompiledGaussian`、merged 段实例化因子表 + 链式合并、
   op 段执行器（measure/channel/refs resolve，自 `circuit.py` 迁移）。
   → verify: `python -c "import cvsim.gaussian.compile"`
2. **`cvsim/gaussian/circuit.py` 改造** — 新增 `compile()`；`run()` 改为
   `self.compile().run(...)`；`_DISPATCH`/`_apply` 迁至 compile.py；
   `_partition` 保留。无行为变化。
   → verify: `pytest tests/test_gaussian_circuit.py tests/test_heterodyne.py`
3. **`tests/test_compile.py` 新建** — naive 对照执行器 + fixtures ①②③
   + 语义测试（返回类型/缺参/ParamRef 未测/params 集合/空电路）。
   → verify: `pytest tests/test_compile.py`
4. **全量回归** — `pytest tests`。
   → verify: 全绿（当前 496 passed 基线）
5. **OCR review** 每 commit（Phase 3.4 mandatory）→ 修 high/medium。

## 评审门

- [ ] fixtures ①②③ 全过，atol=1e-9（fixture ①）
- [ ] 全量回归绿
- [ ] OCR high/medium 清零
