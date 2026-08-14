# dsh-trellis-breadcrumb

Trellis workflow-state 面包屑注入插件（DeepSeek Harness）。每个 agent pre-step 解析 `.trellis/workflow.md` 的 `[workflow-state:STATUS]` 块 + `.trellis/.runtime/sessions/` 活动任务，注入 user-role 上下文 — DSH 版 UserPromptSubmit hook。

## 部署

```powershell
# 1. 拷贝到 profile node_modules（boot loader 解析基座 = profile 目录）
$dst = "$env:USERPROFILE\.dsh\profiles\web\node_modules\@deepseek-ai\dsh-trellis-breadcrumb"
New-Item -ItemType Directory -Path $dst -Force | Out-Null
Copy-Item tools/dsh-trellis-breadcrumb\* $dst -Recurse -Force

# 2. 同步测试副本到安装根（test 的 dsh-llm 只在该处解析）
Copy-Item tools\dsh-trellis-breadcrumb E:\03_Learning\deepseekharness\node_modules\@deepseek-ai\dsh-trellis-breadcrumb -Recurse -Force

# 3. cordis.patch.yml（~/.dsh/profiles/web/）已含 insert 行，缺失则补：
# - insert:
#     - id: trellis-breadcrumb
#       name: '@deepseek-ai/dsh-trellis-breadcrumb'

# 4. 重启 web 进程后生效（HMR 热挂载的是旧代码，模块缓存不失效）
```

注意：放安装根 `node_modules/@deepseek-ai/` 的副本 boot loader 不认（`ERR_MODULE_NOT_FOUND`，解析基座是 profile 目录）— 那里只放测试副本。npm/pnpm 更新会清掉两处副本，重新 Copy-Item 即可。

## 测试

```powershell
# 必须在 dsh 安装根副本运行（@deepseek-ai/dsh-llm 解析）
node E:\03_Learning\deepseekharness\node_modules\@deepseek-ai\dsh-trellis-breadcrumb\test.mjs
```

## 约定

- DSH 会话跑 trellis 脚本前：`$env:TRELLIS_CONTEXT_ID = "dsh-<session.id>"`（session 文件按此 key 落盘）。
- 会话身份找不到时回退最新 session 文件（单用户场景）。
- 非 Trellis 项目零输出；异常 fail-open。
