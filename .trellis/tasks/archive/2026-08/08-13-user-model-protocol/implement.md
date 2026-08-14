# Implement — 动态用户模型协议

## 执行清单

1. **写 `认知适配协议.md`** → 验证：Schema 四字段 + L0-L8 + 来源标记 + last_verified 齐全；回答规则含"最小上下文"路径；更新规则含证据分级与 30 天降级；引用心智模型校准文档 §0/§3 与 CONTEXT.md
2. **写 `user-model.md` 初始种子** → 验证：从心智模型校准文档提炼，四字段非空，source 标注诚实（无证据不标 Verified）
3. **写 `.pi/skills/user-model/SKILL.md`** → 验证：<100 行；description 首句 what + 次句 Use when；三步流程（加载→应用→更新）可执行
4. **写 `.pi/skills/user-model/REFERENCE.md`** → 验证：引用根文档为单一事实源；速查表覆盖 Schema/L0-L8/来源/更新触发器
5. **闭环演练** → 验证：按协议回答一个问题（展示 depth 选择）+ 更新 user-model.md + diff 可见
6. **质量检查** → 验证：skill 结构符合 write-a-skill 规范；文档间引用路径正确；术语不违反 CONTEXT.md
7. **commit** → `feat(user-model): 动态用户模型协议 C层文档 + A层skill`（可拆 C/A 两次提交）

## 验证命令

- skill 行数检查：`wc -l .pi/skills/user-model/SKILL.md`（<100）
- 引用路径检查：确认 REFERENCE.md 相对路径可解析
- 演练 diff：`git diff user-model.md` 展示更新

## 评审关口

- prd 验收标准 1-5 全过 → `task.py start`
- 演练（标准 6）→ commit 前确认
