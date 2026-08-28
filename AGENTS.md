<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

## 认知校准（读 AGENTS.md 必读）

- **术语**（说什么）：[CONTEXT.md](./CONTEXT.md)
- **用户模型**（怎么讲）：[user-model.md](./user-model.md) — 解释前读用户模型，按已知/不确定适配表达（规则在全局技能 `user-model` 内：protocol.md）

## Agent skills

### Issue tracker
Issues 跟踪在 GitHub Issues（repo `JialeZhouxin/cvsim`），用 `gh` CLI。见 `docs/agents/issue-tracker.md`。

### Triage labels
五角色默认标签，字符串 = 角色名。见 `docs/agents/triage-labels.md`。

### Domain docs
单上下文：根 `CONTEXT.md` + `docs/adr/`。见 `docs/agents/domain.md`。
