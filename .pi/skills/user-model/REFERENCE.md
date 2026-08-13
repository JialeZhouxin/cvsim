# User Model 速查表

> 完整规则见项目根 `认知适配协议.md`（单一事实源）。本表只做回答时的快速对照。

## Schema 结构（user-model.md）

```
known:        [{concept, depth, source, last_verified}]
uncertain:    [{concept, depth, source, note}]
current_bottleneck: string | null
preferences:  {analogy, technical_precision, terminology, assumption_explicitness,
               reasoning_steps, information_density, verbosity, 表达顺序, 解释入口, ...}
```

## 深度层级 L0-L8

| 层 | 含义 | 层 | 含义 |
|----|------|----|------|
| L0 | 没听说过 | L5 | 能形式化/数学推导 |
| L1 | 知道名字 | L6 | 能应用 |
| L2 | 能说出直觉 | L7 | 能发现边界/反例 |
| L3 | 理解机制 | L8 | 能迁移 |
| L4 | 能解释因果关系 | | |

## 来源标记

`Assumed`（默认）→ `Inferred`（行为推断）→ `Observed`（用户明确说过/做过）→ `Verified`（用户正确复述/应用/纠错）。无用户证据最高停在 Observed。

## 回答时查表

| 概念状态 | 做法 |
|----------|------|
| known L3+ | 直接用，不解释 |
| known L0-L2 | 一句话带过机制 |
| uncertain / 不在表 | 最小上下文（流水线一环 → 一句话机制 → 只补需要的）|
| 用户困惑 | 下移表达深度，换入口（直觉→数学→代码 往回退），不重新讲 |
| 用户说太简单 | 上移，不再解释 |

## 更新触发器

| 用户行为 | 更新 |
|----------|------|
| 正确复述/应用 | Verified，depth +1~2 |
| 主动解释机制/推导 | Observed，depth +1 |
| 追问为什么 | 该项转 Inferred，记 note |
| 指出 AI 错误 | Verified |
| 明确不懂/要换角度 | → uncertain，depth 降 |
| 30 天未验证 | 标回 Inferred |
| 沉默跳过/没追问 | **不动**（≠懂了） |

## 用户偏好摘要（当前）

直觉 → 数学 → 代码；结构映射四问先行；术语保留；假设显式；类比慎用；数值对账验证；推荐答案+权衡；优先级 准确 > 机制 > 假设 > 负荷 > 简洁。

## 引用链

```
认知适配协议.md ──► 心智模型校准文档.md（§0 四问 / §3.1 / §3.2）
       │
       └─────────► CONTEXT.md（术语）
```
