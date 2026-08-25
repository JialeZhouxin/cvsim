# Laws of UX 设计法则指南

> 本项目 UI 与文档设计的心理学参考手册
> 来源: [https://lawsofux.com/](https://lawsofux.com/) — Jon Yablonski
> 整理日期: 2026-08-04 | 适用项目: cv-photonic-notes（cvsim 模拟器 + Lab UI + 中文教程 + 理论笔记）

---

## 如何阅读本手册

- **★ 经典十条**：原版 Laws of UX 的 10 条核心法则，任何界面设计都应先过一遍。
- **每条结构**：官方定义（英文原文 + 中文释义）→ 要点 → 对本项目的具体应用。
- 本手册是**检查清单**而非教条：设计评审、教程写作、API 设计前，扫一遍对应条目。
- 文档编写遵循「理论笔记纯理论、教程代码带注释」的项目惯例，本文件只谈设计原则。

---

## ★ 1. 审美可用性效应（Aesthetic-Usability Effect）

> 官方定义: Users often perceive aesthetically pleasing design as design that's more usable.
> 中文释义: 用户常常认为外观美观的设计"更好用"——即使客观上功能完全相同。

- **要点**
  - 美观的设计会提高用户的容忍度：小问题被忽略，失败被原谅。
  - 首次印象在 50ms 内形成，且难以逆转；先入为主的"好用"印象会延续到后续交互。
  - 反过来也成立：难看的设计会被认为功能也差。
- **本项目应用**
  - Lab UI 采用 IDE 工作台式布局（三列锁满视口、零滚动、面板内滚动），视觉上"像专业工具"，用户自然信任其数值结果。
  - 热图/Wigner 图配色统一（colormap 固定、dpi 一致），教程图表与 Lab UI 视觉语言保持一致。
  - 数值展示使用等宽字体 + 固定有效位，减少"随手打印"的杂乱感。

---

## ★ 2. 菲茨定律（Fitts's Law）

> 官方定义: The time to acquire a target is a function of the distance to and size of the target.
> 中文释义: 到达目标所需时间取决于目标的距离与大小——目标越大、越近，点击越快。

- **要点**
  - 交互元素（按钮、链接、热区）越大越好；常用操作放在手指/鼠标容易到达的区域。
  - 屏幕边缘与角落是"无限大"目标（指针会被物理边界截停），适合放高频操作。
  - 距离惩罚：把相关操作放在一起（如编辑操作紧邻对象）比远距离移动快得多。
- **本项目应用**
  - Lab UI 的「运行电路」「折叠面板」等高频操作按钮加大热区，面板标题栏整条可点击折叠。
  - 电路编辑器里选中节点后，其操作按钮就近弹出（靠近节点而非远处工具栏）。
  - 节点参数输入框高度 ≥ 28px（触控友好下限），避免"差一点点"点不到。

---

## 3. 选择过载（Choice Overload）

> 官方定义: The tendency for people to have a difficult time making a decision when faced with many options.
> 中文释义: 面对过多选项时，人们难以做出决定，甚至放弃选择。

- **要点**
  - 选项越多，决策越慢、满意度越低；"什么都不选"常常成为默认结果。
  - 应对手段：分组、默认推荐、渐进披露、移除低价值选项。
- **本项目应用**
  - 教程目录按 6 大类分组（VQE、哈密顿量、分子、算法、光量子、高级），而不是平铺 17 个 notebook。
  - Lab UI 面板默认折叠收起，避免一次呈现几十个开关；默认参数即"推荐的物理合理值"。
  - 入门路径只推荐 3 个 notebook 顺序，其余作为"进阶"折叠展示。

---

## 4. 认知偏差（Cognitive Bias）

> 官方定义: People make decisions based on the way options are presented to them.
> 中文释义: 人们根据选项的呈现方式做决定，而非纯理性权衡。

- **要点**
  - 呈现顺序、默认值、措辞都在影响决策——设计者对此负有责任。
  - 锚定效应：先看到的值会成为后续判断的参照；默认值即隐式推荐。
- **本项目应用**
  - API 默认参数即物理标准值（如 ħ=1、真空态、50:50 分束器），把"推荐用法"编码进默认值。
  - 教程中数值表格先给"期望结果"再给代码，让读者锚定目标再验证。
  - 结果展示保持中立：误差用绝对差 + 相对差双指标，不挑好看的数字。

---

## 5. 认知负荷（Cognitive Load）

> 官方定义: The amount of mental resources required to complete a task.
> 中文释义: 完成任务所需的脑力资源总量；负荷越高，学习与操作越吃力。

- **要点**
  - 三种负荷：内在（任务本身难度）、外在（呈现方式引入的）、相关（构建心智模型所需）。
  - 设计目标是削减**外在负荷**——排版、导航、措辞不应增加理解成本。
  - 分块、模式识别、渐进披露是主要削减手段。
- **本项目应用**
  - 教程每节只讲一个概念，长公式拆成"直觉 → 数学 → 代码"三段，不在同一屏堆叠。
  - 三表示（Fock/Gaussian/Bosonic）用同一套场景演示（cross-rep demo），读者只需建立一份心智模型。
  - Lab UI 每个面板一个职责（电路 / 参数 / 结果 / 分析），标题即职责。

---

## 6. 内聚（Cohesion）

> 官方定义: Shared design practices create team alignment and a consistent user experience.
> 中文释义: 共享的设计实践带来团队一致性与统一用户体验。

- **要点**
  - 团队内部统一设计语言，比"每个模块各美各的"更重要。
  - 内聚体现为：一致的组件、一致的术语、一致的交互模式。
- **本项目应用**
  - Lab UI 组件库统一（面板、按钮、数值输入复用同一套样式 token），新增面板零新样式。
  - 项目术语表（CONTEXT.md + 术语表.md）即"内聚的文档侧实现"：教程、API、笔记用词一致。
  - 代码评审清单（CODE_REVIEW_GUIDE.md）承载设计共识，新成员据此对齐。

---

## 7. 色彩心理学（Colour Psychology）

> 官方定义: Colours are associated with specific feelings and emotions.
> 中文释义: 颜色会唤起特定的情绪与联想。

- **要点**
  - 文化语境决定颜色含义（如红色 = 危险/热情/好运，随文化不同）。
  - 品牌色、强调色、语义色（成功/警告/错误）要区分且稳定。
- **本项目应用**
  - 热图/Wigner 图使用感知均匀的 colormap（如 viridis 系），避免彩虹色误导数值判读。
  - 语义色固定：绿色 = 校验通过，红色 = 物理不合法（如非物理协方差矩阵），黄色 = 近似/截断。
  - 教程代码块与图注颜色一致，让读者建立"颜色 → 含义"的稳定映射。

---

## 8. 确认（Confirmation）

> 官方定义: Users should always be given the opportunity to confirm their decisions.
> 中文释义: 用户应始终有机会确认自己的决定，尤其是破坏性操作。

- **要点**
  - 不可逆/代价高的操作必须有确认步骤，且确认要说明后果。
  - 低风险操作加确认反而打断流程，按风险分级使用。
- **本项目应用**
  - Lab UI 中「运行大规模仿真」（如大截断维数 Fock 计算）前弹出确认，附预计内存/时间。
  - API 破坏性变更遵循 Phase 2 API 稳定性策略：弃用警告 → 移除，而非静默删除。
  - 教程 Run-All 前在开头注明运行时长，避免读者中途后悔。

---

## 9. 一致性（Consistency）

> 官方定义: Users are more likely to transfer knowledge and skills from one product to another if they're similar.
> 中文释义: 产品之间越相似，用户越容易迁移已有知识与技能。

- **要点**
  - 内部一致性：同一产品内相同事物用相同表现（命名、排序、行为）。
  - 外部一致性：跟随用户熟悉的生态惯例（IDE、Notebook、计算库）。
- **本项目应用**
  - 三表示 API 对齐：Fock/Gaussian/Bosonic 状态类共用同名方法（measure、analyse、绘制），读者学一种表示即可迁移——这正是 cross-rep demo 的卖点。
  - Lab UI 遵循 IDE 惯例：左侧电路、右侧结果、顶栏状态，用户零学习成本上手。
  - 教程结构模板统一：目标 → 原理 → 代码 → 验证 → 练习。

---

## 10. 好奇心缺口（Curiosity Gap）

> 官方定义: We have a natural tendency to fill a gap in our knowledge, even when the answer isn't that important to us.
> 中文释义: 人们天生想填补知识缺口——知道"不知道"本身就会驱动求知。

- **要点**
  - 先制造缺口（悬念、矛盾、未解问题），再提供答案，学习动机最强。
  - 标题与开头是制造缺口的主战场；缺口必须诚实，不能标题党。
- **本项目应用**
  - 教程标题用问题引导（如"为什么高斯态只需协方差矩阵？"），正文首段先点出认知冲突。
  - 每个教程开头给出"读完你将能回答的三个问题"，结尾回收答案，形成闭环。
  - 目录按"从直觉出发"排序：先让读者发现朴素理解的漏洞，再引入数学。

---

## ★ 11. 多尔蒂阈值（Doherty Threshold）

> 官方定义: Productivity soars when a computer and its users interact at a pace (<400ms) that ensures that neither has to wait on the other.
> 中文释义: 当计算机与用户的交互节奏低于 400ms（彼此无需等待对方）时，生产力飙升。

- **要点**
  - 400ms 是"无缝对话"的阈值；超过后用户会感到等待并开始分心。
  - 无法更快时：给反馈（进度、骨架屏、乐观更新），让用户感觉系统在工作。
- **本项目应用**
  - Lab UI 的小规模电路构建/单次求值目标 <400ms（numpy 后端可达成）；热图渲染走增量更新。
  - 大规模 Fock 计算必然超时：显示进度条 + 已用时间 + 预计剩余，避免"假死"。
  - 折叠/展开面板用 CSS 过渡（原生动画，0 额外成本），保持响应感。

---

## 12. 五帽架（Five Hat Racks）

> 官方定义: Information is harder to understand when it's presented in more than one of the five ways it can be organized.
> 中文释义: 信息有五种组织方式（类别、时间、地点、字母、层级），混用超过一种会降低可理解性。

- **要点**
  - 一次只用一种组织方式；切换视图需显式、可预期。
  - 五种方式：字母序、时间序、类别、层级、地理位置。
- **本项目应用**
  - 教程目录用**层级 + 类别**两级，不混入时间序（新旧教程不按日期排列）。
  - 术语表按类别组织（基础概念 / 表示 / 测量 / 分析），不按字母序堆砌。
  - API 文档按功能分组（状态 / 门 / 通道 / 分析），每组内再字母序——单层规则，可预测。

---

## 13. 灵活性-可用性权衡（Flexibility-Usability Tradeoff）

> 官方定义: The more flexible a system is, the less usable it is.
> 中文释义: 系统越灵活，越难用。

- **要点**
  - 功能膨胀直接伤害可用性：每个选项都是认知负担与出错点。
  - 解法：默认简单 + 可渐进展开高级能力（分层界面）。
- **本项目应用**
  - cvsim 定位教学模拟器：公开 API 刻意少而精（三表示 + 门 + 通道 + 分析），深度选项放底层参数（validate=、atol=）而非常驻参数。
  - Lab UI 默认只露"物理上有意义的旋钮"，推导性参数收进折叠的「高级」区。
  - 教程矩阵（Fock/Gaussian/Bosonic 三列）就是"同一能力三种灵活度"的教学演示。

---

## 14. 目标梯度效应（Goal Gradient Effect）

> 官方定义: The tendency to become more motivated as we get closer to achieving a goal.
> 中文释义: 越接近目标，动力越强。

- **要点**
  - 可见的进度（进度条、步骤指示）显著提升坚持率与速度。
  - 人为制造"已完成感"（如奖励虚拟进度）会放大效应，但须真实。
- **本项目应用**
  - 长教程顶部显示章节进度（X/6），并标注"已完成章节数"。
  - 学习路径明确里程碑：基础入门 → 第一个 VQE → 第一个 GBS → 自由实验，每步有可交付物。
  - Lab UI 仿真完成后显示"✓ 完成"状态与耗时，给用户明确的完成信号。

---

## ★ 15. 希克定律（Hick's Law）

> 官方定义: The time it takes to make a decision increases with the number and complexity of choices.
> 中文释义: 决策时间随选项的数量与复杂度增加而增加。

- **要点**
  - 选项多 → 决策慢，且用户更可能"跳过决策"（用默认）。
  - 削减选项、分组、默认值、渐进披露是标准对策；但完全消除选择也会降低掌控感。
- **本项目应用**
  - 工具栏只放 5±2 个主操作，其余收进溢出菜单。
  - 状态制备（真空/热/压缩/TMSV）用预设按钮而非让用户手填全部参数。
  - 教程每节末尾的练习只给 1-2 道，不给"十选一"。

---

## ★ 16. 雅各布定律（Jakob's Law）

> 官方定义: Users spend most of their time on other sites. This means that they prefer your site to work the same way as all the other sites they already know.
> 中文释义: 用户大部分时间花在别的产品上——他们希望你按他们已经熟悉的方式工作。

- **要点**
  - 不要为了"创新"而背离生态惯例；惯例即已付费的学习成本。
  - 创新应放在内容与体验层，而非交互模式的底层重构。
- **本项目应用**
  - Lab UI 抄袭 IDE 惯例（面板停靠、快捷键、Ctrl+Enter 运行）而非自创。
  - cvsim API 命名对齐主流量子库习惯（h、cnot、bs、measure），读者从 PennyLane/Strawberry Fields 迁移零摩擦。
  - 教程用 Jupyter 生态（notebook、Run-All、魔法命令），跟随读者已有的心智模型。

---

## 17. 共同区域法则（Law of Common Region）

> 官方定义: Elements tend to be perceived into groups if they are sharing an area with a clearly defined boundary.
> 中文释义: 共享一个有清晰边界区域（边框、底色、留白围合）的元素会被感知为一组。

- **要点**
  - 分组优先级：共同区域 > 连接 > 邻近 > 相似（视觉分组的"权重"排序）。
  - 边框/底色/阴影都能制造共同区域，且比间距分组更强。
- **本项目应用**
  - Lab UI 每个面板用边框 + 底色区分区域，电路图、参数区、结果区一眼可辨。
  - 教程中"代码块 + 输出块"共用同一底色容器，暗示二者属于同一实验单元。
  - 热图面板内图例与图共享区域，避免图例被误读为独立数据。

---

## 18. 简约法则（Law of Prägnanz / Law of Good Figure）

> 官方定义: People will perceive and interpret ambiguous or complex images as the simplest form possible, because it is the interpretation that requires the least cognitive effort of us.
> 中文释义: 人们会把复杂/模糊的图像理解为尽可能简单的形式——因为那最省脑力。

- **要点**
  - 视觉系统自动简化：对称、闭合、规整的形状优先被感知。
  - 设计应主动提供"简单的形状"，而不是让用户从杂乱中自己简化。
- **本项目应用**
  - 电路可视化把对称结构画对称（分束器对、干涉仪布局对齐网格）。
  - Wigner/热图默认视角选对称截面（如 x-p 面），呈现最规整的形式。
  - 教程示意图用最小图形语言（圆 = 模式、线 = 耦合），不做无信息量的装饰。

---

## 19. 邻近法则（Law of Proximity）

> 官方定义: Objects that are near, or proximate to each other, tend to be grouped together.
> 中文释义: 距离近的对象会被感知为一组。

- **要点**
  - 空间距离是最廉价、最强大的分组工具。
  - 组间留白 > 组内留白，分组才成立；间距节奏要一致。
- **本项目应用**
  - 节点参数与其所属节点在电路图上紧邻显示，与其它节点的参数拉开间距。
  - 面板内 label 与输入框间距 < 输入框之间的间距，形成"label-输入"绑定。
  - 教程中图注紧跟图，公式紧跟其推导段落，不跨节漂移。

---

## 20. 相似法则（Law of Similarity）

> 官方定义: The human eye tends to perceive similar elements in a design as a complete picture, shape, or group, even if those elements are separated.
> 中文释义: 视觉会把相似元素（同色、同形、同尺寸）感知为整体，即使它们分离。

- **要点**
  - 相似性维度：颜色 > 形状 > 大小 > 纹理（大体排序）。
  - 相似性意味着"同类"：同类元素必须相似，异类元素必须明显不同。
- **本项目应用**
  - 所有"门"按钮同形同色，所有"分析"操作另一色系，一眼区分操作类别。
  - 三类状态对象在教程与 UI 中用固定图标/颜色（Fock=橙、Gaussian=蓝、Bosonic=绿），跨文档稳定。
  - 同一种测量（homodyne/heterodyne）在所有表示中画同一符号，强化"同一物理"。

---

## 21. 统一连接法则（Law of Uniform Connectedness）

> 官方定义: Elements that are visually connected are perceived as more related than elements with no connection.
> 中文释义: 有视觉连接（线、箭头、容器连接）的元素被认为关系更紧密。

- **要点**
  - 连接是分组的最强信号之一，甚至压过邻近与相似。
  - 连接线本身应表达语义：方向、类型（实线/虚线）都要有含义。
- **本项目应用**
  - 电路可视化用实线连"有耦合的模式对"，无耦合模式间不画线，直接传达纠缠结构。
  - 纠缠/信道关系用虚线标注（如 loss 信道），与控制门实线区分。
  - Lab UI 中"仿真结果 → 其来源电路"用连线或面包屑关联，用户可溯源。

---

## ★ 22. 米勒定律（Miller's Law）

> 官方定义: The average person can only keep 7 (plus or minus 2) items in their working memory.
> 中文释义: 普通人工作记忆只能同时容纳 7±2 个项目。

- **要点**
  - 数字本身不必教条（现代研究更保守，4±1），要点是"工作记忆极有限"。
  - 应对：分块（chunking）、外部化（写下来、界面呈现）、分组。
- **本项目应用**
  - 面板参数一屏 ≤7 组；节点参数按「门参数 / 通道参数 / 测量参数」分块折叠。
  - 教程每节要点 ≤5 条，公式推导的中间量用变量名外部化（写全名而非省略号）。
  - 工具栏主操作 5±2 个（与希克定律呼应），溢出项收进菜单（外部化 = 不用记住）。

---

## 23. 奥卡姆剃刀（Occam's Razor）

> 官方定义: Among competing hypotheses, the one with the fewest assumptions should be selected. [设计语境] 面对竞争方案，最简单的那个更可能是对的。
> 中文释义: 若无必要，勿增实体——设计上即"能不做的元素就不做"。

- **要点**
  - 每个多余元素都是一次决策、一次出错机会、一份维护成本。
  - 注意：简单 ≠ 简陋；奥卡姆剃刀针对"无必要"的复杂，不砍必要的功能。
- **本项目应用**
  - 新 API 先问"真的需要吗"（YAGNI）：能复用 measure/analyse 就不新造方法。
  - 教程只保留能运行的代码单元，删除"演示性"但无教学增量的中间步骤。
  - Lab UI 默认隐藏装饰元素（网格线、次要标注），需要时再展开。

---

## 24. 卓越悖论（Paradox of Excellence）

> 官方定义: When a product is excellent at one thing, users expect it to be excellent at everything.
> 中文释义: 产品在某方面越卓越，用户越期待它在所有方面都卓越——期望随表现水涨船高。

- **要点**
  - 单一亮点会抬高整体期望，短板随之更刺眼。
  - 要么全面达标，要么明确告知边界；承诺要诚实、范围要清晰。
- **本项目应用**
  - cvsim 是**教学**模拟器，不是生产级 GBS 工具——文档开头明示能力边界（高斯态为主、截断 Fock、无噪声建模完整集），避免读者拿它做研究仿真后失望。
  - 教程标题不夸大（"理解高斯玻色采样原理"而非"实现商用 GBS"）。
  - API 稳定性文档（api-stability.md）写明"什么承诺、什么不承诺"，管理期望。

---

## ★ 25. 峰终定律（Peak-End Rule）

> 官方定义: People judge an experience largely based on how they felt at its peak and at its end, rather than the total sum or average of every moment of the experience.
> 中文释义: 人们对一段体验的评价，主要取决于**峰值时刻**与**结束时刻**的感受，而非全程平均。

- **要点**
  - 设计"峰值"：一个让人记住的高光时刻（成功反馈、漂亮的可视化）。
  - 设计"结尾"：结束时的心情最影响整体评价；坏的结尾会毁掉整个体验。
- **本项目应用**
  - 教程结尾固定放「收获总结 + 下一步 + 练习答案」，结束在"我能做到了"的高点。
  - 每个 tutorial 的最后一个 cell 输出完整物理结论（数值对账表），而非草草结束。
  - Lab UI 大计算完成时给出"✓ 完成 + 耗时 + 关键结果摘要"的峰值反馈。

---

## 26. 图像优势效应（Picture Superiority Effect）

> 官方定义: Pictures and images are more likely to be remembered than words.
> 中文释义: 图像比文字更容易被记住。

- **要点**
  - 图文结合的记忆效果显著优于纯文字（记忆保持率约 6:1 的说法广为流传，机制属实：双通道编码）。
  - 图要有信息量，不能是装饰；无关图反而分散注意。
- **本项目应用**
  - 教程以图为中心组织：每个概念先给 Wigner 函数/热图/电路图，再给公式。
  - 三表示的对照实验用同一场景三张图并排（cross-rep demo），图像对比即教学。
  - 术语表配微型示意图（如 |n⟩ 的 Fock 分布图），强化记忆锚点。

---

## 27. 波斯特尔定律（Postel's Law / 鲁棒性原则）

> 官方定义: Be liberal in what you accept, and conservative in what you send.
> 中文释义: 宽容地接受输入，谨慎地产生输出。

- **要点**
  - 输入侧：容忍合理的变体（类型转换、缺省补全、宽松格式）。
  - 输出侧：只发出严格、规范、无歧义的内容。
  - 宽容要有边界：物理不合法输入必须报错，而非静默接受。
- **本项目应用**
  - cvsim 参数解析宽容：`angle` 接受 float / tensor / list，缺省用物理标准值；但协方差矩阵非物理时**必须报错**（validate= 默认开）。
  - 输出侧严格：数值带单位约定（ħ=1 明示）、atol 默认值明确、文档字符串给出输出形状与语义。
  - Lab UI 输入框对"带单位的数字"宽容解析（"0.5" 与 "1/2" 都接受），但结果显示统一格式。

---

## 28. 渐进披露（Progressive Disclosure）

> 官方定义: A strategy for managing information complexity — only show the necessary information, and provide additional information on demand.
> 中文释义: 只显示当下必要的信息，其余按需展开——管理信息复杂度的策略。

- **要点**
  - 默认视图只承载核心任务；细节、高级项、推导过程延迟到用户请求。
  - 披露层级要有明显入口（"展开推导"按钮），且状态可预期。
- **本项目应用**
  - Lab UI 折叠面板 = 渐进披露的落地：默认只露结果与主参数，推导/中间量在 <details> 内。
  - 教程把数学推导折叠进"推导细节（可选）"块，主线保持直觉 → 结论。
  - API 文档先给一屏能看完的快速上手，再分页给完整签名。

---

## 29. 心理安全（Psychological Safety）

> 官方定义: Psychological safety is the belief that you won't be punished or humiliated for speaking up with ideas, questions, concerns, or mistakes.
> 中文释义: 心理安全 = 相信提想法、问问题、承认错误不会受到惩罚或羞辱。

- **要点**
  - 对产品：错误信息不应羞辱用户（"你操作错误！"→"这一步需要…"）。
  - 对团队/社区：贡献者敢提问、敢质疑，才有真正的质量反馈。
- **本项目应用**
  - 错误信息分级措辞：校验失败提示"参数不满足物理条件（V + iΩ ≥ 0 被违反），建议：…"，附修复建议而非指责。
  - 教程练习的"常见错误"板块主动列出坑（如截断维数太小导致负概率），让读者犯错时不慌。
  - 代码评审指南鼓励"对事不对人"的发现式评审（findings → 修复，而非指责）。

---

## 30. 红色效应（Red Effect）

> 官方定义: The colour red affects human behaviour and physiology — increasing heart rate, evoking urgency and alertness.
> 中文释义: 红色影响行为与生理——升高心率、唤起紧迫感与警觉。

- **要点**
  - 红色 = 强烈信号：错误、危险、紧急、关键数值。
  - 滥用红色会制造持续焦虑，并稀释其警示效力（狼来了效应）。
- **本项目应用**
  - 红色只用于：物理不合法、计算失败、数值发散——高优先级信号。
  - 校验警告（非致命）用黄色，成功用绿色，形成三级语义色阶。
  - 教程中"注意：此近似在低截断下失效"这类风险提示用红色边框，但每节最多 1-2 处。

---

## 31. 倒摄干扰（Retrospective Interference）

> 官方定义: Retroactive interference occurs when newly learned information interferes with the recall of previously learned information.
> 中文释义: 新学的信息会干扰对旧信息的回忆。

- **要点**
  - 相似的新知识会覆盖/混淆旧知识——尤其是命名相近、概念相邻的内容。
  - 教学上对策：显式对比新旧差异、建立区分锚点、错开学习时间。
- **本项目应用**
  - 术语表（CONTEXT.md）为每对易混概念写显式区分（如 homodyne 不删模 vs heterodyne 删模；mode 重映射语义）。
  - 教程中引入新表示时，先给"它与前一种表示的三点不同"，再展开。
  - 三表示的命名刻意统一（同方法名）但标注表示类型，防止"学了 Gaussian 忘了 Fock"。

---

## 32. 序列位置效应（Serial Position Effect）

> 官方定义: Users have a propensity to best remember the first and last items in a series.
> 中文释义: 人们最容易记住序列中的**第一个**和**最后一个**项目（首因效应 + 近因效应）。

- **要点**
  - 最重要的信息放开头与结尾；中间部分记忆最弱。
  - 长列表、长文、长演示都应把关键结论安排在首尾。
- **本项目应用**
  - 教程每节结构：开头给目标（要记住的），结尾给总结（要记住的），中间是过程。
  - 长教程目录把"入门"放第一、"总结/下一步"放最后，中间按依赖排序。
  - 教程运行输出的末尾 cell 打印核心数值对账表——读者最后看到的是结论。

---

## 33. 施奈德曼黄金法则（Shneiderman's Golden Rules）

> 官方定义: Eight principles of interface design: (1) strive for consistency, (2) seek universal usability, (3) offer informative feedback, (4) design dialogs to yield closure, (5) prevent errors, (6) permit easy reversal of actions, (7) support internal locus of control, (8) reduce short-term memory load.
> 中文释义: 界面设计八原则：一致性、普适可用性、信息反馈、对话闭环、错误预防、可逆操作、用户掌控感、减轻短期记忆负担。

- **要点（八条逐一）**
  1. 一致性：相同事物相同表现（见第 9 条）。
  2. 普适可用性：照顾新手与专家（新手走引导，专家走快捷键）。
  3. 信息反馈：每个操作都有结果反馈。
  4. 对话闭环：操作序列有明确的开始-结束信号（如"已保存"）。
  5. 错误预防：在设计层面阻止错误发生（校验、约束），而非事后报错。
  6. 可逆操作：能撤销就撤销（删除 → 回收站）。
  7. 用户掌控感：用户是操作主体，系统不擅自决定。
  8. 减轻短期记忆：界面呈现信息，别让用户记（见米勒定律）。
- **本项目应用**
  - 1：三表示 API 一致性；2：教程有"5 分钟快速版"与完整版；3：每次求值显示耗时与状态；4：仿真从"运行"到"✓ 完成"有完整闭环；5：参数输入即时校验（非物理值当场标红）；6：Lab UI 删除节点可撤销；7：仿真参数全部用户可控，系统只做建议；8：常用配置可保存复用，不用重输。

---

## 34. 泰斯勒定律（Tesler's Law / 复杂度守恒定律）

> 官方定义: Tesler's Law, also known as the Law of Conservation of Complexity, states that for any system there is a certain amount of complexity that cannot be reduced.
> 中文释义: 任何系统都有不可削减的固有复杂度；你能做的是把它放在哪一侧。

- **要点**
  - 复杂度守恒：要么让用户承担，要么让开发者/系统承担。
  - 好设计把复杂度从用户侧搬走——但必须诚实：不是"消除"了复杂度，而是"转移"了。
- **本项目应用**
  - cvsim 把"三表示的物理复杂度"收进内部实现（协方差演化、hafnian 计算），用户侧只剩 3-4 个方法。
  - Lab UI 把"模式索引重映射"等概念复杂度内置，界面只显示物理上有意义的参数。
  - 诚实边界：转移不了的复杂度（如截断维数的选择）必须显式暴露给用户并给引导。

---

## 35. 威胁检测（Threat Detection）

> 官方定义: The brain is hardwired to detect threats, which can influence how users interact with a product.
> 中文释义: 大脑天生优先检测威胁，这会影响用户与产品的交互。

- **要点**
  - 威胁信号（刺眼弹窗、红色警报、猝不及防的音效）触发战斗/逃跑反应，抢占认知资源。
  - 只在真实威胁时触发；虚假警报会训练用户忽略（习惯化）。
- **本项目应用**
  - 只有"计算会不收敛/物理不合法/数据将丢失"才弹强提示，日常状态用安静的信息条。
  - 数值发散警告给出具体数值证据（哪个参数、多少量级），而非泛泛的"警告！"。
  - 教程不制造虚假紧迫感（无"现在必须学！"式文案），保持可信度。

---

## 36. 时间感知（Time Perception）

> 官方定义: The way users perceive time affects how they experience a product.
> 中文释义: 用户对时间的**感知**（而非真实耗时）决定体验。

- **要点**
  - 等待的感知可被设计：进度反馈、分块加载、娱乐性占位都让等待"变短"。
  - 不透明的等待最痛苦；明确告知"还要多久"大幅改善体验。
- **本项目应用**
  - 长计算显示进度百分比 + 剩余估算（基于已完成比例，可诚实计算）。
  - 教程标注每个 notebook 的预计运行总时长（顶部 banner），管理读者时间预期。
  - Lab UI 中首次加载显示骨架屏，避免白屏被感知为"卡死"。

---

## 37. 系统状态可见性（Visibility of System Status）

> 官方定义: The system should always keep users informed about what is going on, through appropriate feedback within a reasonable time.
> 中文释义: 系统应始终让用户知道正在发生什么（合理时间内给出适当反馈）。

- **要点**
  - 每个操作都应有状态反馈：进行中 / 成功 / 失败 / 空闲。
  - 反馈要具体（"正在对角化 12×12 矩阵…"优于"加载中"）。
- **本项目应用**
  - Lab UI 状态栏常驻：当前电路状态（构建中/已求值/含噪声）、后端（numpy）、耗时。
  - 求值完成显示"结果就绪"并高亮结果面板，提示用户可继续下一步。
  - API 层面：构建电路的方法返回电路对象（链式可见），求值方法返回带元数据的结果（含耗时、截断信息）。

---

## ★ 38. 冯·雷斯托夫效应（Von Restorff Effect / 隔离效应）

> 官方定义: The Von Restorff effect, also known as The Isolation Effect, predicts that when multiple similar objects are present, the one that differs from the rest is most likely to be remembered.
> 中文释义: 在一堆相似对象中，最与众不同的那个最容易被记住。

- **要点**
  - 突出 = 记忆：需要用户注意的元素可以用差异化（颜色、尺寸、形状）制造。
  - 反用：不需要注意的元素应保持同质——到处都突出 = 什么都不突出。
- **本项目应用**
  - 教程中每个"关键警告/关键结论"用统一的、唯一的高亮样式（每节 1 处），其余文字同质。
  - Lab UI 主操作按钮用强调色（其余次级按钮中性色），主次一眼可分。
  - 三表示对照表中"差异点"列用高亮，相同点列保持素色——差异即记忆点。

---

## 39. 泽伊加尔尼克效应（Zeigarnik Effect）

> 官方定义: People remember uncompleted or interrupted tasks better than completed tasks.
> 中文释义: 人们记住未完成/被打断的任务，比记住已完成的任务更牢。

- **要点**
  - 未完成感是强大的参与引擎：进度条、待办清单、"差一步"提示都利用它。
  - 风险：未完成太多会产生焦虑；要在"钩住"与"放手"间平衡。
- **本项目应用**
  - 教程每节结尾留一个"你自己的实验"（开放任务），让读者带着未完成感离开，下次自然回来。
  - 学习路径显示"未完成章节"标记，但明确允许跳过（不制造负罪感）。
  - Lab UI 中未运行的参数修改显示"未应用"标记，提醒但不强制。

---

## 40. 工具定律（Law of the Instrument）

> 官方定义: If the only tool you have is a hammer, it's tempting to treat everything as if it were a nail.
> 中文释义: 如果你只有一把锤子，看什么都像钉子——工具会塑造你的解法偏好。

- **要点**
  - 熟悉的技术会被过度使用，即使它不是最优解。
  - 设计上：给用户提供"不止一把锤子"，并帮助判断何时用哪把。
- **本项目应用**
  - 这正是三表示设计的理论依据：Fock（精确但昂贵）、Gaussian（高效但只覆盖高斯态）、Bosonic（灵活近似）——教程教读者**按问题选表示**，而非只会一种。
  - 教程矩阵提供"问题类型 → 推荐表示"决策表，对抗单一工具倾向。
  - cvsim 内部不因"高斯快"就回避 Fock 教学：同一演示三种表示都算，读者看到代价差异。

---

## 附：经典十条速查卡

设计评审 30 秒自检，对照本项目的 Lab UI / 教程 / API：

| # | 法则 | 一句话检查 |
|---|------|-----------|
| 1 | 审美可用性效应 | 界面整洁美观吗？数值展示是否统一？ |
| 2 | 菲茨定律 | 高频按钮大且近吗？折叠区好点吗？ |
| 11 | 多尔蒂阈值 | 小操作 <400ms 吗？大操作有进度吗？ |
| 15 | 希克定律 | 主操作 ≤7 个吗？有默认值吗？ |
| 16 | 雅各布定律 | 遵循 IDE / Jupyter / 量子库惯例吗？ |
| 22 | 米勒定律 | 参数分组了吗？信息外部化了吗？ |
| 23 | 奥卡姆剃刀 | 每个元素/API 都有存在理由吗？ |
| 25 | 峰终定律 | 结尾停在成功总结吗？有峰值反馈吗？ |
| 27 | 波斯特尔定律 | 输入宽容、输出严格吗？非法输入报错吗？ |
| 34 | 泰斯勒定律 | 固有复杂度转移给系统了吗？残余的暴露了吗？ |
| 38 | 冯·雷斯托夫效应 | 关键信息有唯一高亮吗？高亮不超过 1-2 处吗？ |
| 39 | 泽伊加尔尼克效应 | 有未完成钩子吗？有适度放手吗？ |

---

## 附：与项目既有约定的对应

| 项目文档 | 对应的法则 |
|---------|-----------|
| `docs/api-stability.md` | 波斯特尔、泰斯勒、确认、卓越悖论 |
| `docs/vision-gaussian-lab-ui.md` | 审美可用性、菲茨、共同区域、渐进披露、系统状态可见性 |
| `docs/lab-interaction.md` / `lab-drag-ux.md` | 菲茨、希克、统一连接 |
| `CONTEXT.md` 术语表 | 倒摄干扰、内聚、五帽架 |
| 教程模板（目标→原理→代码→验证→练习） | 序列位置、峰终、泽伊加尔尼克、好奇心缺口 |
| cross-rep demo（三表示同一场景） | 一致性、工具定律、图像优势 |
| `CODE_REVIEW_GUIDE.md` | 心理安全、内聚 |

---

*本手册整理自 lawsofux.com（Jon Yablonski）。经典十条为其原版内容，其余为站点扩展法则。应用示例结合 cv-photonic-notes 项目实际编写。*
