# DSH Trellis 适配 — Technical Design

## Architecture

两层适配，互不依赖：

### A 层：技能迁移（零 DSH 改动）

`cp -r .claude/skills/trellis-* → .agents/skills/`。DSH `dsh-skill-filesystem` 扫 `<projectRoot>/.agents/skills`（rank 200），watcher 检测变更 → 发布替换目录。frontmatter `name` 保持 `trellis-*`（kebab-case 合规，模型目录即按此名展示）。

边界：复制品与 `.claude/` 原件重复（双份）。Trellis `update` 只管理 `.claude/` 平台文件（.template-hashes.json 哈希表），`.agents/skills/` 不在其管理面 → 升级后需手动重同步。接受（可写重同步脚本，非本 task 范围）。

### B 层：面包屑注入插件（DSH 扩展路径）

**包**：`dsh-trellis-breadcrumb`（放在项目 `tools/dsh-trellis-breadcrumb/`，file: 依赖进 profile）。

**挂载**：`~/.dsh/profiles/web/package.json` dependencies 加 `"dsh-trellis-breadcrumb": "file:E:/02_Projects/turingQ/cv-photonic-notes/tools/dsh-trellis-breadcrumb"` → pnpm install → `cordis.patch.yml` 向 standard preset 组合插入一行（id: trellis-breadcrumb, name: dsh-trellis-breadcrumb）。shipped 文件零改动。

**插件逻辑**（模仿 dsh-tool-skill 的 pre-step 形态）：
1. `agent/pre-step` 监听，取调用会话 cwd。
2. 定位项目根（含 `.trellis/` 的最近祖先；无 → 静默返回，零注入）。
3. 解析 `.trellis/workflow.md` 全部 `[workflow-state:STATUS] ... [/workflow-state:STATUS]` 块。
4. 解析活动任务：`.trellis/.runtime/sessions/<context-key>.json`（context key 从 `TRELLIS_CONTEXT_ID` env 或 session 元数据取）→ task.json.status；无活动任务 → `no_task`。
5. 命中块 → 注入 user-role 指令上下文：`Active task: <path>\n<块正文>`（块缺失 → 通用行 "Refer to workflow.md for current step."，与官方 hook 降级语义一致）。
6. 注入防抖：同状态连续轮次不重复注入（digest 比较，参照 skill-catalog 的 digest 机制）。

**数据流**：pre-step → 插件 → 读文件（fs）→ 注入 user-role 持久消息（模型可见，GUI 上下文注入区可查）。

## Contracts

- 注入文本格式：`<workflow-state>` 包裹，与 inject-workflow-state.py 输出兼容（status 块正文 + Active task 行）。
- 活动任务解析失败（文件损坏）→ 降级 no_task 文本，不吞错误也不抛异常。
- 非 Trellis 项目：0 输出，0 副作用。

## Compatibility / Migration

- A 层：与 `.claude/` 共存无冲突（DSH 不读 `.claude/`，Claude Code 不读 `.agents/`）。
- B 层：插件只读文件 + 注入上下文，不注册工具、不占 catalog。DSH 升级：profile package.json + cordis.patch.yml 是用户层，升级保留；插件包 file: 依赖随项目走。
- 回滚：A 层删 `.agents/skills/trellis-*`；B 层删 patch 行 + 移除依赖 + pnpm install。均即时生效（热刷新 / 重启）。

## Trade-offs

- 面包屑无强制力（模型可能忽略注入），与官方 hook 相同性质（提示非门禁）。
- 插件注入成本：每轮一次文件读 + digest 比对，可忽略。
- 手动 `TRELLIS_CONTEXT_ID` 每命令前缀：写进 skill 用法/工作流约定，比改脚本侵入小。

## Operational Notes

- 验证需要 DSH web 进程重启（插件挂载在启动时读取）。重启后新 pre-step 注入生效；本会话预检（当前 task 已激活，status=planning → 注入 planning 块）。
- pnpm 在 profile 目录可用（dsh plugin 命令转发 pnpm）。
