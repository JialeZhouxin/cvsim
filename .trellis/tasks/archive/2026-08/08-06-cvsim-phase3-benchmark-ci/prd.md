# m=100 benchmark + CI

## Goal

vision Phase 3 exit #2 + #5：m=100 compile+apply 性能**落地为可执行回归**——基准脚本 + `benchmarks/` 记录 + CI time-capped job。F-COMPILE 归档 PRD 明确「性能基准归 benchmark-ci」。

## Background（已确认事实）

- `cvsim/gaussian/compile.py` 已就绪：`GaussianCircuit.compile() -> CompiledGaussian`，`compile()` O(n_ops) 切段；`run()` 对 merged 段 `_instantiate` 一次构建大 S + 一次 `apply_symplectic`
- `tests/test_compile.py` 有独立 naive 参考执行器（`naive_run`，走 `_run_op` 逐 op）——等价性已测（atol=1e-10）
- `.github/workflows/ci.yml` 现有 4 job：lint (ruff) / type-check (mypy 3.10+3.12) / test (pytest 3.10–3.13 + coverage 3.12) / api-freeze——**无 benchmark job**
- `benchmarks/` 目录不存在
- **本地实测**（scripts/_bench_tmp.py，seed=42，repeat=3 best）：
  - m=100 depth=50：naive 92.7ms / compiled 40.0ms（2.3x）
  - m=100 depth=100：naive 159.9ms / compiled 142.4ms（1.1x）
  - m=32 depth=100：13.5 / 10.7ms；m=300 depth=50：1.61s / 0.77s（2.1x）
  - 编译优势：省逐 op 的 S 构造 + validate 开销；`_instantiate` 每次 run 重建 S（`compile()` 切段本身 ~0.05ms）
- vision L539：random depth-100 passive circuit on m=32 与未编译匹配 atol=1e-9 且 benchmark fixture 更快

## Requirements（brainstorm 收敛）

- R1: 基准脚本 `benchmarks/benchmark_m100.py`（或同目录等价）：随机 depth-100 被动电路 m=100，测 compile 时间 + compiled run 时间 + naive 时间（复用 test_compile 的 naive 模式），repeat=3 取 best
- R2: 结果写 `benchmarks/latest.json`：m/耗时/加速比/随机种子/git commit/时间戳——跨 commit 回归可见
- R3: CI 新增 benchmark job（GitHub Actions）：m=100 compile+run 全流程 **hard fail 阈值 2s**（本地实测 0.14s，14x 余量，容忍 CI 机器噪声）；naive 对比**不硬断言**（depth=100 仅 1.1x 余量，防 flaky），只记录加速比
- R4: 预算常量可配置（环境变量/CLI 参数），默认 2.0s
- R5: 脚本支持 `--m` 参数（默认 100；300/1000 本地手动用，CI 只跑 m=100）——vision L705 m=10³ target 留口

## Acceptance Criteria

- [ ] 基准脚本可运行：`python benchmarks/benchmark_m100.py`（或统一入口）退出 0，写 latest.json
- [ ] latest.json 含全部 R2 字段，格式稳定（版本字段）
- [ ] CI benchmark job 存在且过（push 到 master 后实测验证）；超预算时 exit 非 0
- [ ] 与 F-COMPILE 等价性约束衔接：脚本内校验 compiled vs naive atol=1e-10（naive 复用 test_compile 参考实现）
- [ ] 全量 pytest 绿；每 commit OCR high/medium 清零

## Out of Scope

- 编译正确性（F-COMPILE 已归档，`34d83e2`）
- Walrus/GBS interop（gbs-decision）
- 内存 profile（vision L705 m=1000 32MB 记录为远期目标，非本任务）

## Notes

- PRD 聚焦需求；需 design.md + implement.md 后才能 start（本任务含 CI 改动 + 新目录 + 阈值，按复杂任务处理）
