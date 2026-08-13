# User Model（动态状态）

> Schema 与规则见 [认知适配协议.md](./认知适配协议.md)。本文件每轮对话后更新。
> 来源标记：Observed（用户明确说过/做过）/ Inferred（从行为推断）/ Assumed（默认）/ Verified（验证过）。

**版本**: 0.1
**最后更新**: 2026-08-13（初始种子，来自心智模型校准文档访谈 Q1-Q12 + 用户设计文档）

---

## known

| 概念 | depth | source | last_verified |
|------|-------|--------|---------------|
| 三表示结构（G/F/B 各自的 V,r̄ / 截断振幅 / 分量混合） | L5 | Observed（用户亲自补全四维切分） | 2026-08-13 |
| 三表示成本（O(m²) / N^m / O(K·m²)） | L5 | Observed | 2026-08-13 |
| 实验流水线叙事（源 → 操作 → 测量） | L6 | Observed（用户锁定的中心锚点） | 2026-08-13 |
| 场景驱动教学组织（不按表示排序） | L5 | Observed | 2026-08-13 |
| 表示选型规则（测量类型为判据） | L5 | Observed | 2026-08-13 |
| 数值对账验证法（三表示数字一致 = 对了） | L6 | Observed | 2026-08-13 |
| 决策维度表法（列选项→列维度→逐维打勾） | L5 | Observed | 2026-08-13 |
| Wigner 函数 / 密度矩阵连接三表示 | L3 | Observed | 2026-08-13 |
| 结构映射四问（流水线/表示/直觉/对账） | L6 | Observed | 2026-08-13 |
| 具身类比体系（橡皮泥、手电筒、地形图） | L4 | Observed | 2026-08-13 |
| 认知脚手架/教学系统设计（User Model、诊断、支架、验证闭环） | L5 | Observed（用户独立写出完整设计文档） | 2026-08-13 |

## uncertain

| 概念 | depth | source | note |
|------|-------|--------|------|
| （领域概念待填充） | — | — | 初始种子诚实原则：无用户证据不捏造。首次领域对话后按 §3 补录 |
| 表达触发型：跳过直觉直接上公式/术语时容易丢失 | L2 | Inferred（反模式清单 §3.2 用户锁定 5 条反模式，说明此类表达曾造成卡顿） | 回答时先直觉后公式 |

## current_bottleneck

`null`（待对话填充。填充规则：一次一个，解决后清空）

## preferences

| 字段 | 值 | source |
|------|----|--------|
| analogy（类比） | 低：具身/空间化直觉可以，过度简化类比不要 | Observed |
| technical_precision | 高 | Observed |
| terminology | retain：术语保留，中文交流，必要英文加中文注释 | Observed |
| assumption_explicitness | 高：讨厌 unexplained jumps，2+ 未说明假设会卡 | Observed |
| reasoning_steps | 中高 | Inferred |
| information_density | 中 | Inferred |
| verbosity | adaptive | Inferred |
| 表达顺序 | 直觉 → 数学 → 代码 | Observed（§2.1） |
| 解释入口 | 结构映射四问先行，禁教科书顺序 | Observed（§0） |
| 决策格式 | 推荐答案 + 权衡 | Observed（§2.3） |
| 验证方式 | 数值对账为主，写/讲为辅 | Observed（§2.2） |
| 优先级 | 准确 > 机制保留 > 假设显式 > 负荷适度 > 简洁 | Observed（用户原文） |

## 对话日志（最近）

- 2026-08-13 访谈：锁定心智模型校准文档全部规则（Q1-Q12）
- 2026-08-13 设计对话：用户明确目标 = 回答适配（非教学 Agent）；拍板落盘 user-model.md
- 2026-08-13 本任务：四点目标拍板（单用户 / 先 C 后 A / 现有框架当图谱 / 非教学 Agent）；用户纠正我的"教学 Agent"表述 → 精确纠偏能力（Observed）；一次批准"开干" → 决策果断、方案清晰即放行（Observed）
