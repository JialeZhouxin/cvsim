# Phase 5 implement — Bridges & CV error-correction

## 执行策略

4 child 串行（单一 writer），每 child：测试先行 red→green → 全量 pytest 回归 → trellis-check（subagent）→ commit → OCR review（服务端不稳时 trellis-check 兜底）→ archive → start 下一 child。

## Child 计划

### C1: phase5-bridge（bridge 数学）
- `cvsim/bridge.py`：5 函数（coherent_element / squeezed_element / thermal_diag / vacuum_probability / fock_state_amplitude）
- `tests/test_bridge.py`：解析 vs Fock 数值对照（coherent/squeezed/thermal/vacuum prob）+ 已知解析值硬编码
- 先查 `cvsim/fock/` 工厂 API（coherent/squeezed/thermal 态构造名）
- verify: `pytest tests/test_bridge.py` → 全量 700 基线 + 新增全绿
- commit: `feat(bridge): F-BRIDGE 观测值桥 — 矩阵元/真空概率解析函数族 + 对照测试`

### C2: phase5-threshold（threshold outcome-only）
- `cvsim/gaussian/observables.py`：`p_click` / `sample_threshold`（_vacuum_probability 内联，公式同 bridge 注释互链）
- `cvsim/gaussian/circuit.py`：`measure_threshold(mode, name)` builder
- `cvsim/gaussian/compile.py`：threshold op 编译路径（outcome → values，段断点）
- `tests/test_threshold.py`：p_click vs Fock 截断（真空/相干/挤压）；采样分布（seed 固定）；builder+run 链路；IndexError/非高斯输入
- verify: 新测试绿 + 全量回归
- commit: `feat(measure): threshold outcome-only — p_click/sample_threshold + circuit builder + 编译链路`

### C3: phase5-gkp-tutorial（GKP 纠错教程）
- `tutorials/_build_06.py` + `06_gkp_feedforward.ipynb`（6 节，Run-All 可执行，含自检断言）
- `tests/test_gkp_tutorial.py`：教程关键数值回归（读出≈2ε、修正后方差下降）
- verify: 全单元 Run-All 实测（exec 提取 code cell）+ 全量回归
- commit: `feat(tutorial): 06 GKP feedforward — CZ+measure+ParamRef 纠错闭环教程`

### C4: phase5-bosonic-consistency（三表示互证）
- `tests/test_bosonic_consistency.py`：合同固化（vacuum/加权矩/loss/单分量）+ 桥锚定（cat/GKP ⟨x⟩/Var 三向对照）
- verify: 新测试绿 + 全量回归
- commit: `test(bosonic): consistency 合同固化 + cat/GKP 桥锚定三向对照`

## 收口（C4 后）

- vision v0.4.0：Phase 5 close + exit 1/2 打 ✅ + gap table（Fock/Bosonic 行更新、F-BRIDGE/threshold 行 Done）+ changelog
- CONTEXT.md：bridge 观测值桥、threshold outcome-only 术语补充
- spec：backend 无关（bridge/threshold 进 spec 如质量指南 contract 表）
- parent archive + add_session

## 风险点

| 风险 | 缓解 |
|------|------|
| Fock 工厂 API 名不确定 | C1 开工先 grep `cvsim/fock/__init__.py` |
| squeezed_element 公式符号（φ 约定） | 对照 FockState.squeezed 实现取同一约定，测试锁死 |
| vacuum_probability 与 observables 双份公式漂移 | 同一测试数值互锁（解析 vs 解析互测） |
| GKP 教程"读出≈2ε"物理推导偏差 | C3 先数值标定再写进教程断言 |
| OCR 服务端不稳 | 既定兜底：trellis-check + 全量 pytest（Phase 4 同款） |

## 验证命令

```bash
.venv/Scripts/python.exe -m pytest tests -q            # 全量
.venv/Scripts/python.exe -m pytest tests/test_X.py -q  # 单 child
.venv/Scripts/python.exe tutorials/_build_06.py        # 教程构建
# Run-All 实测：python -X utf8 提取 code cells 执行（Phase 4 同款脚本）
```
