# DSH Platform Integration Spec

DSH（DeepSeek Harness）环境下的 Trellis 工作流适配。Trellis 官方支持平台列表不含 DSH；本 spec 记录适配契约，防止未来会话重复踩坑。

## Scenario: DSH 运行 Trellis

### 1. Scope / Trigger

- Trigger: 在 DSH GUI 会话中按 Trellis 工作流执行任务（task.py / 技能 / 面包屑）。
- 平台差异：DSH 无 UserPromptSubmit hook、不扫 `.claude/`、无 `py` 启动器、子代理用 `subagent` 工具。

### 2. Signatures

```powershell
# 脚本一律用项目 venv（`py` 启动器在 DSH 沙箱被拒）
$py = "E:\02_Projects\turingQ\cv-photonic-notes\.venv\Scripts\python.exe"

# 会话身份（约定：dsh-<session.id>，写 .trellis/.runtime/sessions/<key>.json）
$env:TRELLIS_CONTEXT_ID = "dsh-a0a78738e15e"
& $py .trellis/scripts/task.py create "<标题>" --slug <name>
& $py .trellis/scripts/task.py start <name>
& $py .trellis/scripts/task.py current --source
```

### 3. Contracts

- **技能安装位置**：项目 `.agents/skills/trellis-*`（DSH rank 200，项目作用域，热刷新；不从 `.claude/skills` 读）。frontmatter 不得改动；`trellis update` 不管理该目录，升级后手动重同步。
- **面包屑插件**：`@deepseek-ai/dsh-trellis-breadcrumb`，源码 `tools/dsh-trellis-breadcrumb/`，部署副本在 **`~/.dsh/profiles/web/node_modules/@deepseek-ai/`**（boot loader 的解析基座是 profile 目录；放安装根 node_modules 会被 `ERR_MODULE_NOT_FOUND` 拒绝）；`cordis.patch.yml` 以 `- insert:` 挂载；**代码更新必须真重启**（HMR 能热挂行，但依赖追踪跳过 node_modules，模块缓存不失效，挂的是旧代码）。
- **注入消息**：user-role，`source: { kind: "trellis-breadcrumb", form: "text" }`，文本 = `Active task: <path>` + `<workflow-state:STATUS>` 块（正文取自 `.trellis/workflow.md` 标签，单源）。
- **子代理派遣**：`subagent` 工具，prompt 首行 `Active task: <task path from task.py current>`，主体用 `.claude/agents/trellis-{implement,check,research}.md` 内容。
- **运行中 web 进程**：`node <dsh安装根>/node_modules/@deepseek-ai/dsh/lib/bin.js web`；安装根即 `E:\03_Learning\deepseekharness\node_modules`（bundle 与插件都从该处解析）。

### 4. Validation & Error Matrix

| 条件 | 行为 |
|---|---|
| cwd 向上无 `.trellis/workflow.md` | 插件零输出，不注入 |
| workflow.md 缺 `[workflow-state:STATUS]` 标签 | 注入通用行 `Refer to workflow.md for current step.` |
| `.runtime/sessions/` 无文件 / current_task 为空 | 按 `no_task` 块注入 |
| task.json 损坏 | status 降级 `planning`，不抛异常 |
| 同状态连续轮次 | digest 相同，不重复注入 |
| 插件内部异常 | fail-open：log + 不注入，不阻断步骤 |

### 5. Good/Base/Bad Cases

- Good: `task.py start` 后下一轮注入 `<workflow-state:in_progress>` + Active task 行。
- Base: 无活动任务 → 注入 `no_task` 块，无 Active task 行。
- Bad: 在 `~/.agents/skills` 装技能（全局污染其他项目）；`py -3` 跑脚本（沙箱拒绝）；改 `.claude/skills` frontmatter（`trellis update` 会覆盖）。

### 6. Tests Required

- `node tools/dsh-trellis-breadcrumb/test.mjs`（部署副本同文件）：断言 ①首次注入含 `Active task` + `<workflow-state:in_progress>` ②同状态去重 ③非 Trellis cwd 静默 ④新 agent 首轮注入。运行环境：dsh 安装根（`@deepseek-ai/dsh-llm` 解析）。

### 7. Wrong vs Correct

#### Wrong
```powershell
py -3 ./.trellis/scripts/task.py start 08-14-dsh-trellis-adapt   # Access is denied
```

#### Correct
```powershell
$env:TRELLIS_CONTEXT_ID = "dsh-a0a78738e15e"
.\.venv\Scripts\python.exe ./.trellis/scripts/task.py start 08-14-dsh-trellis-adapt
```

## Design Decisions

### 插件部署：安装根 node_modules 直放，不走 profile file: 依赖

**Context**: profile `node_modules` 为空、`autoInstallPeers: false`、离线安装风险；bundle 解析顺序为 dsh 安装根优先。

**Options**:
1. profile `package.json` file: 依赖 + pnpm install
2. 安装根 `node_modules/@deepseek-ai/` 直接放置包目录（当前）

**Decision**: 方案 2 — 零安装步骤，模块从安装根 hoisted 解析；代价是 npm 更新会清掉，重部署 = 重新 Copy-Item（README 有记录）。

### 会话身份约定 `dsh-<session.id>`

**Context**: task.py 需要 context key；DSH 无 hook 输入。脚本原生支持 `TRELLIS_CONTEXT_ID` env 覆盖（active_task.py:391）。

**Decision**: 命令前 export `TRELLIS_CONTEXT_ID=dsh-<session.id>`；插件按同 key 找 session 文件，找不到回退最新文件。约定不写进脚本，写在 spec。

## Gotchas

> **Warning**: DSH 补丁层按 id 替换整行 `config`，无深合并 — 覆盖行必须重述全部字段。
>
> **Warning**: `trellis update` 只管理 `.claude/` 平台文件；`.agents/skills/` 与 `tools/dsh-trellis-breadcrumb/` 的手动同步是长期维护点（升级后需重拷贝 + 重部署插件）。
>
> **Warning**: 插件改动后必须重启 web 进程才生效（HMR 只重跑 apply()，不重载 node_modules 模块）。重启后验证：stderr 无 `ERR_MODULE_NOT_FOUND`，且状态变更后下一轮 pre-step 上下文出现 `<workflow-state:*>` 块。
>
> **Warning**: 测试从安装根副本跑（`E:\03_Learning\deepseekharness\node_modules\@deepseek-ai\dsh-trellis-breadcrumb\test.mjs`）— `@deepseek-ai/dsh-llm` 只在该处可解析；profile 副本仅用于加载。改动后两处都要同步。
