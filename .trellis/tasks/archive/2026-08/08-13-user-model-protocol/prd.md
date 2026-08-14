# PRD — 动态用户模型协议（C 层文档 + A 层 skill）

## 背景

用户长期与 AI 协作学习 CV 光量子计算。现有静态资产：
- `CONTEXT.md` — 术语白名单（说什么）
- `心智模型校准文档.md` — 认知框架（怎么想、怎么说），2026-08-13 一次访谈锁定

问题：静态文档不随对话演化。AI 只能按固定规则说话，不知道用户**当前**哪里不确定、哪些概念已验证、偏好是否漂移。

用户设计目标（2026-08-13 对齐，四点拍板）：
1. 服务对象：用户本人（单用户模型）
2. 落地形态：先 C（协议文档）后 A（pi skill）
3. 初始图谱：用现有框架（三表示 + 结构映射四问）当初始图谱
4. **最终目的不是教学 Agent**，而是：用文档 + skill 让 agent 更了解用户，回答时用用户能理解的语言——不降精度、不堆术语、不假设用户懂

状态落盘（用户拍板）：建 `user-model.md`，每次对话后更新，跨会话累积。

## 范围

### 做

**C 层（本次交付）**
1. `认知适配协议.md`（项目根，稳定协议）：
   - User Model Schema 定义（known / uncertain / current_bottleneck / preferences + 深度层级 L0-L8 + 来源标记 Observed/Inferred/Verified + last_verified 时间戳）
   - 回答适配规则（何时解释术语、何时保留术语、如何用结构映射四问、解释深度选择）
   - 模型更新规则（什么算证据、何时升级/降级、保守原则：没追问 ≠ 懂了）
2. `user-model.md`（项目根，动态状态）：按 Schema 实例化的初始种子，从心智模型校准文档 + 历史记忆提炼

**A 层（本次交付，参考 write-a-skill 规范）**
3. `.pi/skills/user-model/` skill：SKILL.md（<100 行）+ REFERENCE.md（协议速查，引用根文档为单一事实源）

### 不做

- 教学 Agent 机制：错误诊断器、理解验证层、主动补课、Scaffolding 深度控制器
- 知识依赖图（跨概念 prerequisite 图谱）
- 代码实现（无 Python 模块、无 schema 校验脚本）
- 多用户 / 多领域支持

## 约束

- 与 `心智模型校准文档.md` 分工：它是静态认知框架（怎么想、怎么说），新协议文档管动态状态（用户现在在哪）+ 更新机制；后者引用前者，不复制内容
- 术语遵守 `CONTEXT.md` 白名单
- skill 遵循 write-a-skill 规范：SKILL.md < 100 行、description 首句 what it does + 次句 Use when [triggers]、引用一层深
- 文档用中文，技术术语保留原文（用户偏好：机制优先、术语保留、少类比）

## 验收标准

1. `认知适配协议.md` 定义完整 Schema：known / uncertain / current_bottleneck / preferences 四字段 + L0-L8 深度层级 + 来源标记（Observed/Inferred/Verified）+ last_verified 机制
2. 回答适配规则可执行：明确"用户未知概念出现时怎么做"（不是简单降深度，而是按结构映射补最小上下文）
3. 更新规则可执行：证据分级、保守降级（last_verified 过期）、Observed 优先于 Inferred
4. `user-model.md` 初始种子非空：从心智模型校准文档提炼 known/uncertain/bottleneck/preferences，每字段有真实内容
5. skill 可加载：description 含触发词（用户模型、认知校准、怎么讲、如何解释等），SKILL.md < 100 行，REFERENCE.md 引用根协议文档
6. 闭环演练：按协议回答用户一个问题 + 更新 `user-model.md`（演示一轮完整 loop）

## 交付形态

- 3-4 个新文件（2 文档 + skill 2 文件），不动现有文档内容
- commit 一次（C 层）或两次（C 层 + A 层），可合并
