# Bosonic 架构设计 — 实施计划

## 任务性质

文档任务：grill A1–A12 已完结（2026-08-14 会话内），本任务负责落盘 + 同步。无代码。

## 检查清单

1. [x] grill A1–A12 逐题锁定（12/12 采纳推荐答案）
2. [x] `design.md` 落盘（决策总表 + 模块架构 + 理由/权衡/B 映射）
3. [x] `prd.md` 定稿
4. [ ] vision-bosonic-simulator.md §3 模块树 amend（A4：measure.py 合并、observables 只留矩、component_eng 补 is_hermitian）+ §11 文档控制追加
5. [ ] `docs/adr/0006-bosonic-architecture.md`（A5 CDF 反演 + A8 initial 工厂规格）
6. [ ] CONTEXT.md 增补术语：weight_sum 归一化、is_hermitian、CDF 网格反演
7. [ ] user-model.md 会话日志追加（grill 决策特征）
8. [ ] implement.jsonl / check.jsonl 补 context 条目（vision/ADR-0005/design.md）
9. [ ] 用户复核 design.md（review gate）→ `task.py start` → 复核通过即 `task.py finish` + archive（无代码实施）

## 验证命令

```powershell
py -3 ./.trellis/scripts/task.py validate 08-14-bosonic-architecture
```

## 回滚点

- 全部产出为文档；git revert 即可。vision amend 单独 commit，便于剥离。
