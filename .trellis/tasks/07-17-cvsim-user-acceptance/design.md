# Design · 最终用户验收

## 1. Scope

| 内 | 外 |
|----|----|
| `cvsim/USER_ACCEPTANCE.md` | 新物理功能 |
| `cvsim/demos/user_acceptance.py` | 理论笔记改写 |
| README 链接 | Circuit / 量子库 |

## 2. Architecture

```text
cvsim/USER_ACCEPTANCE.md     # 目标 + U1–U6 + 未做（人读）
cvsim/demos/user_acceptance.py  # U1–U5 可执行检查（机跑）
cvsim/README.md              # 链
README.md                    # 链（短）
```

Demo 结构（最小）：

```python
checks = [u1, u2, u3, u4, u5]  # each -> (name, ok: bool, detail: str)
# run all; print table; exit(0 if all ok else 1)
```

U6 仅文档命令（pytest 留给用户/CI）；demo 不强制 subprocess pytest（避免依赖 pytest 安装路径吵）。

## 3. Scenario → 代码映射

| 场景 | 复用 |
|------|------|
| U1 | `GaussianState.vacuum`；`det_cov`；约定常量 |
| U2 | `squeeze`；`mean_photon`；`homodyne_var` |
| U3 | `displace`；`beamsplitter`；`phase` |
| U4 | Fock `squeeze` + cutoff 扫描趋势 |
| U5 | `even_cat`；`weight_sum`；`phase` |
| U6 | 文档 shell |

## 4. Doc skeleton

```text
# 最终用户验收
## 项目目标
## 约定
## 环境
## U1 … U5（短代码 + 期望）
## U6 机器门禁
## 一键
## 未做 / 规划
## 版本与更新约定
```

## 5. Trade-offs

| 选择 | 原因 |
|------|------|
| 汇总再 exit | 一次看全红绿 |
| demo 不含 pytest | 少耦合 |
| 文档在 cvsim/ | 工程验收贴代码 |

## 6. Test strategy

- 跑 demo 期望 exit 0  
- 全量 pytest 回归  
- 可选：对 demo 内 assert 逻辑做极薄自检（非必须）
