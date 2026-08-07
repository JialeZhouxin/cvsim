# benchmarks

`m=100` compile-vs-naive 基准 + CI 时间预算（vision Phase 3 exit #2/#5）。

## 运行

```bash
python benchmarks/benchmark_m100.py            # m=100, depth=100, budget 2.0s
python benchmarks/benchmark_m100.py --m 300    # 本地手动看大 m（CI 只跑 m=100）
python benchmarks/benchmark_m100.py --budget 0.5
```

退出码：`0` 过 · `2` 超预算 · `3` 编译/naive 不等价。

## 阈值依据

本地实测 m=100 depth=100 compile+run ≈ **0.11s**；预算 2.0s ≈ 18x 余量，
CI runner 噪声（通常 ≤3x）安全。超预算 = 无意性能回归，CI 红。

## 输出

`latest.json`（schema 1）——m/耗时/加速比/commit/时间戳。提交时选择性
`git add` 作跨 commit 快照。naive 对比只记录不硬断言（depth=100 加速仅
1.1–2.2x，硬断言易 flaky）。

## 依赖私有 API

naive 路径用 `cvsim.gaussian.compile._run_op`（非公共面，无稳定性承诺）。
等价性由 `tests/test_compile.py` 冻结；若 `_run_op` 签名漂移，本脚本 import
即失败并提示。
