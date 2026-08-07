# m=100 benchmark + CI — Implementation

## 依赖序

脚本 → 本地验证 → CI job → 全量验证 → 归档。单一 commit（+ 可能的 OCR fix commit）。

## 1. benchmarks/benchmark_m100.py

- [ ] argparse：`--m`（默认 100）、`--depth`（默认 100）、`--budget`（默认 2.0）、`--seed`（默认 42）
- [ ] 随机被动电路生成器（squeeze/phase/bs/mz，seed 固定）——从 scripts/_bench_tmp.py 提炼
- [ ] naive 路径：`_run_op` 逐 op 循环（`GaussianState.vacuum` 起）
- [ ] 校验：compiled.V vs naive.V atol=1e-10，rbar atol=1e-12；不等 → exit 3
- [ ] repeat=3 best 计时；budget 检查 → 超时 exit 2（消息含实测）
- [ ] 写 `benchmarks/latest.json`（schema 1，字段见 design.md）
- [ ] README.md：跑法、阈值语义（14x 余量依据）、私有 API 依赖注明
- verify: `python benchmarks/benchmark_m100.py` → exit 0 + latest.json 生成；`--m 300` 手动 OK
- [ ] 删除 scripts/_bench_tmp.py（临时文件，不提交）

## 2. CI job（.github/workflows/ci.yml）

- [ ] 新增 `benchmark` job（ubuntu-latest + py3.12，`pip install ".[dev]"`，跑脚本）
- [ ] job 级 timeout-minutes: 10 兜底
- verify: 本地跑脚本模拟；push 后 GitHub 实测（PR 或直 push 后查 Actions 结果）

## 3. 收口

- [ ] 全量 pytest + node 测试绿（零改动预期）
- [ ] OCR review → high/medium 清零
- [ ] 选择性 git add（benchmarks/ + .github/workflows/ci.yml + latest.json 快照）→ commit
- [ ] `task.py archive` + add_session.py 记录

## 风险

- GitHub Actions 首次跑失败（workflow 语法/安装）——push 后立即查 Actions 日志
- CI runner 慢到超 2s：余量 14x，几乎不可能；若发生调预算并记录
- `_run_op` 私有签名漂移：README 注明 + 跑前 smoke（脚本内 import 即验证）
