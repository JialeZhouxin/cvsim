# DSH Trellis 适配 — Implementation Plan

## Ordered Checklist

1. ✅ 建 task + prd.md + design.md（本文件）
2. **task.py start**（工件齐备后）
3. **A 层**：复制 9 个 `.claude/skills/trellis-*` → `.agents/skills/`；验证目录结构 + frontmatter 原样
4. **B 层**：读 `dsh-tool-skill/lib/index.js` 提取 pre-step 注入 API 形态（插件注册、user-role 注入、digest）
5. **B 层**：写 `tools/dsh-trellis-breadcrumb/`（package.json + lib/index.js）
6. **B 层**：profile package.json 加 file: 依赖 → pnpm install → cordis.patch.yml 挂载到 standard preset
7. **B 层**：重启 DSH web，验证 pre-step 注入（本会话 planning 状态块可见）
8. **check**：trellis-check 语义（spec 合规 + 验证命令）；验证命令见下
9. **update-spec**：捕获适配知识到 `.trellis/spec/`（DSH 平台适配指南）
10. **OCR review**：本 task 每个 commit `ocr review --audience agent --commit <hash>`，报告存 `{TASK_DIR}/ocr-<hash>.txt`
11. **commit**：工件 + 技能 + 插件分批提交（work commits → archive → journal）
12. **finish-work**：archive + add_session

## Validation Commands

```powershell
# A 层
Get-ChildItem .agents/skills -Directory | Select Name          # 9 个 trellis-*
# 目录热刷新：下一轮会话 <available_skills> 出现 trellis-* 条目（人工确认）

# B 层（重启后）
# GUI 上下文注入区可见 <workflow-state:planning> 块（人工确认）
# 插件零输出验证：在非 Trellis 目录开会话，上下文无注入

# 身份链路
$env:TRELLIS_CONTEXT_ID="dsh-<sid>"; .venv\Scripts\python.exe .trellis\scripts\task.py current --source
# → session:dsh-* 

# 全流程
.venv\Scripts\python.exe .trellis\scripts\task.py list
.venv\Scripts\python.exe .trellis\scripts\task.py validate 08-14-dsh-trellis-adapt
```

## Risky Files / Rollback Points

| 文件 | 风险 | 回滚 |
|---|---|---|
| `.agents/skills/`（新增） | 无（纯新增目录） | 删目录 |
| `tools/dsh-trellis-breadcrumb/`（新增） | 无 | 删目录 |
| `~/.dsh/profiles/web/package.json` | 依赖破坏 web 启动 | 移除依赖行 + pnpm install |
| `~/.dsh/profiles/web/cordis.patch.yml` | patch 语法错误 | 清空为 `[]` |
| `~/.dsh/profiles/web/node_modules`（pnpm install 产物） | 可重装 | pnpm install |

## Pre-start Checklist

- [ ] prd.md 收敛完成（无 TBD、无重复）
- [ ] design.md 覆盖架构/契约/回滚
- [ ] implement.md 覆盖步骤/验证/风险
- [ ] 用户已批准进入实现（A+B 范围 + 项目级技能目录已确认）
