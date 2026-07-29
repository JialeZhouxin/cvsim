# Implement: Phase 1 退出 demo

## 前置已完成
- [x] brainstorm 收敛（Q1–Q5 全 resolved）
- [x] PRD 收敛 pass
- [x] design 数学锁定 + 可行性预演（TMSV/4模链/5/6/9 项 sim 与手算一致实测）

## 执行步骤 (ordered)
1. **建 venv 跑 pytest 绿**
   - 命令：`py -3 -m venv .venv` 或 uv（AGENTS.md 要求 uv）：`uv venv && uv pip install -e . pytest numpy scipy`
   - 验证：`uv run pytest -q` 退出码 0（Phase 1 退出第 4 条）
   - **风险点**：仓库根目录 `pyproject.toml` 是否存在/可装；若不存在改用 `pip install -e` 或 sys.path.insert(0,'.') 方案（与预演一致）。
2. **写 `examples/phase1_exit_demo.py`**
   - 结构：imports → 参数固定 → 源构造 → BS → loss → 取对账量 → analytic 表 → assert
   - 每对账项前注释标 analytic 表达式来源（指向 design.md §手算对账清单）
   - 实现失败对比表打印函数 + raise
3. **跑脚本验收**
   - 命令：`py -3 examples/phase1_exit_demo.py`
   - 验证：退出码 0；无 stderr 输出（成功路径零输出）；无 stdout（all 过 atol）
   - 故障模拟：故意改 analytic 一个数 → 跑 → 应打对比表 + raise
4. **勾选愿景 §5 Phase 1 退出第 3 条**
   - 在 `docs/vision-gaussian-simulator.md` §5 Phase 1 段加 demo 已做标记，或新建 `docs/phase1-exit-demo.md` 存手算记录（取后者，不污染 vision doc 主体）
5. **任务收尾**
   - `py -3 ./.trellis/scripts/task.py finish`（或保持 active 等用户验收后 finish + archive）

## 验证命令一览
```bash
# 阶段 1
uv venv && uv pip install -e . pytest numpy scipy
uv run pytest -q                      # 期望: 全绿, 250+ passed

# 阶段 3
py -3 examples/phase1_exit_demo.py    # 期望: exit 0, 静默
py -3 -c "import numpy as np; print(np.__version__)"   # 环境健康码
```

## 风险/回滚点
- **R1: pytest 不绿** → demo 做完不能宣称 Phase 1 退出第 4 条。回滚：先修暴露的失败测试，再回头跑 demo。
- **R2: 某 atol 不过** → 按设计 §风险与回滚点 打印三阶段 V 矩阵定位分叉处；若证明是 cvsim bug（非手算口误）→ 视作真实 regression，立任务追因，不掩盖 Raise。
- **R3: uv venv 装不上** → fallback `py -3 -m venv`；或仓库预演已用 sys.path.insert 路线，demo 自身不依赖 venv（脚本内 import cvsim 总能通过 sys.path 在仓库根跑）。但 pytest 验证阶段需真 venv。

## 实施后检查（task.py start 之前）
- [ ] implement.jsonl 含至少一条真 spec/research 条目（非 _example 种子）→ skills/trellis-brainstorm §Artifact Rules
- [ ] check.jsonl 同上
- [ ] 用户验收或明示 go 实现
