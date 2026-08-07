# m=100 benchmark + CI — Design

## Architecture

```
benchmarks/
  benchmark_m100.py     # 基准脚本（唯一入口，--m 参数）
  latest.json           # 每次运行结果快照（git 选择性 add 作为回归历史）
  README.md             # 简短说明（如何跑/阈值语义）
.github/workflows/ci.yml  # + benchmark job（hard fail 2s, 只跑 m=100）
```

无库代码改动（cvsim/ 不动）——纯基准设施。naive 参考用 `cvsim.gaussian.compile._run_op` 私有 API（benchmark 非公共面，等价性已有 test_compile.py 冻结）。

## 脚本契约

`python benchmarks/benchmark_m100.py [--m 100] [--depth 100] [--budget 2.0] [--seed 42]`

- 电路：随机被动 op（squeeze/phase/beamsplitter/mach_zehnder，seed 固定可复现），复现实测用生成器逻辑
- 测量（repeat=3 取 best，同 _bench_tmp）：
  - `t_compile`：`circ.compile()`（O(n_ops) 切段）
  - `t_compiled_run`：`circ.compile().run()`
  - `t_naive`：逐 op `_run_op` 循环（未编译路径）
- 校验：compiled vs naive 状态 atol=1e-10（与 test_compile.py 同档）
- 硬断言：`t_compile + t_compiled_run <= budget` 否则 exit 2（消息含实测值）
- 输出 `latest.json`：

```json
{
  "schema": 1,
  "m": 100, "depth": 100, "seed": 42,
  "commit": "<git rev-parse HEAD>",
  "timestamp": "ISO-8601",
  "t_compile_s": 0.00009, "t_compiled_run_s": 0.142,
  "t_naive_s": 0.160, "speedup": 1.13,
  "budget_s": 2.0, "passed": true
}
```

- naive 对比**不硬断言**（Q1 决策：depth=100 仅 1.1x 余量防 flaky），只记录 speedup

## CI job

```yaml
benchmark:
  name: Benchmark (m=100, budget 2s)
  runs-on: ubuntu-latest
  steps: checkout → setup-python 3.12 → pip install ".[dev]" → python benchmarks/benchmark_m100.py
```

- 独立 job（与 test 并行，不拖慢）；time-capped 由脚本内 budget 承担（GitHub Actions job 级 timeout 另设 10m 兜底）
- CI 只跑 m=100（Q2 决策）；`--m 300/1000` 本地手动

## 阈值依据

本地实测 m=100 depth=100：compile+run ≈ **0.14s**（best of 3）。budget 2.0s = 14x 余量；CI ubuntu runner 通常 ≤3x 本地慢速。Lint/type-check 均已在跑，benchmark job 无新依赖。

## Trade-offs

| 选项 | 结论 |
|------|------|
| hard fail vs soft 记录 | 宽松 hard（2s）+ JSON 记录（Q1） |
| naive 对比硬断言 | 不（1.1x 边缘 flaky），仅记录（Q1） |
| CI m 梯度 | 只 m=100；脚本 --m 支持 300/1000（Q2） |
| naive 实现 | `_run_op` 私有 API（非公共面；test_compile 已冻结等价） |
| latest.json 跟踪 | 不 gitignore——每次跑后 git status 会脏，commit 时选择性 add 作快照（跨 commit 回归历史） |

## Compatibility

- cvsim/ 零改动；测试零改动；仅新增 benchmarks/ + ci.yml job
- `_run_op` 签名若变 → benchmark 脚本同步（私有 API 无稳定性承诺，README 注明）
