# Phase 5 C2 — Threshold outcome-only

## Goal

`cvsim/gaussian/observables.py` 加 threshold 测量（grill Q3 锁定：outcome-only，解析式）。GKP 教程（C3）的检测功能前置。

## Requirements

- `observables.p_click(state, mode)` → float：1 − 0 光子概率（`_vacuum_probability` 私有内联，公式与 bridge.vacuum_probability 同源、注释互链）
- `observables.sample_threshold(state, mode, rng)` → bool：`rng.random() < p_click`
- `GaussianCircuit.measure_threshold(mode, name=None)` builder；compile.py 编译路径（outcome 0/1 入 values，段断点，同 homodyne 机制）
- **outcome-only**：无态更新（grill 2026-08-10），docstring 显式标注；后验更新 ponytail
- 校验：GaussianState 输入；mode 越界 IndexError
- `tests/test_threshold.py`：p_click vs Fock 截断（真空/相干/挤压）；采样分布（固定 seed）；builder + compile().run(values) 链路（含 ParamRef 引用 threshold outcome）；越界/类型错误

## Acceptance Criteria

- [ ] AC1: p_click 与 Fock 截断对角元一致（atol 1e-10 量级）
- [ ] AC2: 采样分布正确（固定 seed 统计）
- [ ] AC3: circuit builder + 编译 + ParamRef 链路可运行
- [ ] AC4: 全量 pytest 绿；commit + OCR
