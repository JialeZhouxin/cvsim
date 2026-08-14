# DSH Trellis 工作流适配

## Goal

将 Trellis 工作流（v0.6.6，native workflow）完整适配到 DeepSeek Harness (DSH) 环境，使 DSH 会话具备与 Claude Code 等官方平台等价的工作流能力：trellis-* 技能可加载、每轮 workflow-state 面包屑注入、子代理派遣、会话身份可用。适配过程本身走 Trellis task 全流程，作为端到端验证。

## Background / Confirmed Facts

- 项目已 `trellis init`（v0.6.6），Claude Code 平台文件在 `.claude/`：9 个 `trellis-*` 技能、3 个子代理 md（trellis-implement/check/research）、hooks（含 inject-workflow-state.py）、2 个斜杠命令。
- DSH 只扫描 `.dsh/skills`（rank 100）与 `.agents/skills`（rank 200）作为项目技能根，不扫 `.claude/`；技能目录热刷新（watcher + 变更发布替换目录）。
- DSH 无 UserPromptSubmit hook；插件系统为 cordis 组合，pre-step 监听（dsh-tool-skill 同款机制）可注入 user-role 上下文。
- DSH 扩展官方路径：`~/.dsh/profiles/web/package.json`（out-of-tree 插件依赖）+ `~/.dsh/profiles/web/cordis.patch.yml`（组合补丁层）。
- Trellis 脚本原生支持 `TRELLIS_CONTEXT_ID` env 覆盖会话身份（active_task.py:391）；已实测 `task.py create` 用 `TRELLIS_CONTEXT_ID=dsh-<session>` 成功激活。
- 子代理派遣：DSH `subagent` 工具 + `.claude/agents/*.md` 内容作为 prompt。
- 脚本用 `.venv\Scripts\python.exe` 运行（`py` 启动器在沙箱被拒）。

## Requirements

- R1 技能安装位置为**项目级** `.agents/skills/`（用户确认；DSH rank 200 项目作用域，随 git 提交）。
- R2 9 个 `trellis-*` 技能全部迁移，references 子目录完整保留，SKILL.md frontmatter 不改动。
- R3 每轮 pre-step 注入 workflow-state 面包屑：解析 `.trellis/workflow.md` 的 `[workflow-state:STATUS]` 块 + 活动任务（`.trellis/.runtime/sessions/`），注入形态与官方 hook 输出一致；非 Trellis 项目零输出。
- R4 注入插件走 DSH 官方扩展路径（profile package.json 依赖 + cordis.patch.yml 挂载），不改 node_modules 内 shipped 文件。
- R5 子代理派遣用 DSH `subagent` 工具，prompt 前缀 `Active task: <path>` + `.claude/agents/*.md` 内容。
- R6 会话身份：运行 trellis 脚本前设 `TRELLIS_CONTEXT_ID`（不要求改脚本）。
- R7 验证：本 task 全流程（planning→start→implement→check→update-spec→OCR→commit→finish-work）在 DSH 中跑通。

## Acceptance Criteria

- [ ] A1 `.agents/skills/` 下 9 个 `trellis-*` 技能目录齐全（含 references），frontmatter 未改动
- [ ] A2 技能目录热刷新：下一轮会话目录出现 `trellis-*` 条目
- [ ] A3 插件注入面包屑：DSH 会话上下文可见 `<workflow-state>` 块（GUI 上下文注入区可查）
- [ ] A4 非 Trellis 项目/目录插件零输出（不破坏其他会话）
- [ ] A5 `task.py current --source` 返回 `session:dsh-*`（身份链路通）
- [ ] A6 本 task 走完 archive + journal（finish-work 成功）

## Out of Scope

- `trellis channel` 多代理运行时（当前 workflow 为 native，不需要）
- `/trellis:continue`、`/trellis:finish-work` 斜杠命令注册（DSH 命令注册表，后续再说）
- `trellis mem` 会话召回
- 技能 frontmatter 定制、workflow.md 修改

## Open Questions

- 无阻塞项。插件挂载后需重启 DSH web 进程生效（部署时验证）。
