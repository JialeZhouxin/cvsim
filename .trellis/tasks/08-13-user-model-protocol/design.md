# Design — 动态用户模型协议

## 文件布局

```
cv-photonic-notes/
├── 认知适配协议.md          # C 层 · 稳定协议（Schema + 回答规则 + 更新规则）
├── user-model.md            # C 层 · 动态状态（每轮对话后更新，git 跟踪）
└── .pi/skills/user-model/
    ├── SKILL.md             # A 层 · 触发 + 三步流程（<100 行）
    └── REFERENCE.md         # A 层 · 协议速查（引用根文档，不复制全文）
```

## 文档分工（依赖链）

```
心智模型校准文档.md  ──静态框架（怎么想、怎么说）──┐
                                                 ├──► 认知适配协议.md（Schema+规则，引用前者）
CONTEXT.md  ────────术语白名单（说什么）─────────┘              │
                                                                ▼
                                                     user-model.md（状态实例）
                                                                ▲
                                                     skill 加载/应用/更新
```

- `认知适配协议.md` = 稳定层：定义 Schema、L0-L8、来源标记、回答规则、更新规则。引用 `心智模型校准文档.md`（§0 四问、§3.1、§3.2 反模式清单）和 `CONTEXT.md`，不复制。
- `user-model.md` = 动态层：Schema 的实例。结构：头部元信息（版本、最后更新）→ known → uncertain → current_bottleneck → preferences。每项带 depth + source + last_verified。
- skill = 操作层：加载 user-model.md → 回答时应用协议 → 对话后更新 user-model.md。REFERENCE.md 存协议速查表，完整规则指向根文档。

## 关键设计决策

### D1：协议与状态分离
- 理由：协议稳定（几周不变），状态每轮变。合一会让 diff 噪声淹没协议。
- 后果：两个根文档；skill 只写状态文件。

### D2：单一事实源
- skill 的 REFERENCE.md 引用根协议文档，不复制全文（write-a-skill 规范：引用一层深）。
- 理由：协议改一处即生效，无同步漂移。

### D3：初始种子来源
- known / preferences 主要从 `心智模型校准文档.md` 提炼（Q1-Q12 已锁定的认知框架 = 已知 + 偏好证据）。
- uncertain / current_bottleneck 从本次对话 + 记忆提炼（用户对 dot-product-as-similarity 类问题的敏感度是历史证据，但不可凭空捏造——无证据则留空标注）。
- 种子全部标 source=Observed（来自访谈记录）或 Inferred（来自记忆），不标 Verified（未经后续验证）。

### D4：更新规则要点（写入协议）
- 升级证据：用户正确复述/应用概念（Observed→Verified）；主动解释机制（升 depth）
- 降级证据：明确表示不懂；last_verified 超期（默认 30 天）降 confidence 并标 Inferred
- 禁止：把"没追问"当作"懂了"；把一次 Inferred 当 Verified
- 每轮对话结束由 agent 更新；单轮内多次交互，合并且去重

### D5：回答适配规则要点（写入协议）
- 用户未知概念（uncertain/unknown）出现时：**不展开整章**，按结构映射给最小上下文（它在流水线哪一环 → 一句话机制 → 术语保留作标注），然后继续
- 已知概念：直接使用，不解释（除非用户要求）
- 偏好冲突时优先级：概念正确 > 机制保留 > 假设显式 > 认知负荷适度 > 简洁（用户原话：准确 > 好听 > 简单）
- 检测到不确定概念时，回答尾部可带一句轻量确认（"这点先跟上了吗，没跟上我换个角度"）——不是考试，是给用户台阶

## 回答规则中的"不做"

- 不主动补前置课（用户拍板：非教学 Agent）
- 不做诊断分类（8 类失败不实现）
- 不做 L0-L8 主动推进（depth 只用于选择表达深度，不用于规划教学序列）

## Skill 结构（write-a-skill 规范）

```
.pi/skills/user-model/
├── SKILL.md       # <100 行：frontmatter(name+description) → 快速开始 → 三步流程 → 引用
└── REFERENCE.md   # 协议速查：Schema 表、L0-L8、来源标记、更新触发器
```

- description 模板：首句 what it does，次句 "Use when [triggers]"
- 触发词：认知校准 / 怎么讲 / 如何解释 / 用户模型 / 我不懂 / 换个角度 / 太简单 / 太复杂 等

## 回滚形状

- 全部为新文件，不动现有文档 → 回滚 = 删文件，零波及
- `user-model.md` 由 git 跟踪，状态可回退

## 演练验证（验收 6）

- 交付后立即演示一轮：用户问一个问题 → 按协议回答（展示 depth 选择 + 最小上下文）→ 更新 user-model.md → diff 可见
