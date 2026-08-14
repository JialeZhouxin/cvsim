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

## 深度层级（3 档）

| 档 | 含义 | 回答行为 |
|----|------|----------|
| 浅 | 没听说过/知道名字/能说直觉 | 一句话带过机制 |
| 中 | 理解机制/能解释因果 | 直接用，补一句因果 |
| 深 | 能形式化/应用/迁移 | 直接用，可上数学/代码 |

## 来源标记

`Inferred`（行为推断）→ `Observed`（用户明确说过/做过）→ `Verified`（用户正确复述/应用/纠错）。无用户证据最高停在 Observed。

## 回答时查表

| 概念状态 | 做法 |
|----------|------|
| known 深/中 | 直接用（深可上数学，中补因果） |
| known 浅 | 一句话带过机制 |
| uncertain / 不在表 | 最小上下文（流水线一环 → 一句话机制 → 只补需要的）|
| 用户困惑 | 下移表达深度，换入口（直觉→数学→代码 往回退），不重新讲 |
| 用户说太简单 | 上移，不再解释 |

## 更新触发器

| 用户行为 | 更新 |
|----------|------|
| 正确复述/应用 | Verified，档位提升（浅→中→深） |
| 主动解释机制/推导 | Observed，档位提升 |
| 追问为什么 | 该项转 Inferred，记 note |
| 指出 AI 错误 | Verified |
| 明确不懂/要换角度 | → uncertain，降档 |
| 30 天未复验 | 按浅一档处理，提示复验 |
| 沉默跳过/没追问 | **不动**（≠懂了） |

## 用户偏好摘要（当前）

直觉 → 数学 → 代码；结构映射四问先行；术语保留；假设显式；类比慎用；数值对账验证；推荐答案+权衡；优先级 准确 > 机制 > 假设 > 负荷 > 简洁。

## 引用链

```
认知适配协议.md ──► 心智模型校准文档.md（§0 四问 / §3.1 / §3.2）
       │
       └─────────► CONTEXT.md（术语）
```
