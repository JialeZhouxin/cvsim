# dsh-trellis-breadcrumb

Trellis workflow-state 面包屑注入插件（DeepSeek Harness）。每个 agent pre-step 解析 `.trellis/workflow.md` 的 `[workflow-state:STATUS]` 块 + `.trellis/.runtime/sessions/` 活动任务，注入 user-role 上下文 — DSH 版 UserPromptSubmit hook。

## 部署

```powershell
# 1. 拷贝到 dsh 安装根（模块从该处 hoisted 解析）
Copy-Item tools/dsh-trellis-breadcrumb E:\03_Learning\deepseekharness\node_modules\@deepseek-ai\dsh-trellis-breadcrumb -Recurse -Force

# 2. cordis.patch.yml（~/.dsh/profiles/web/）已含 insert 行，缺失则补：
# - insert:
#     - id: trellis-breadcrumb
#       name: '@deepseek-ai/dsh-trellis-breadcrumb'

# 3. 重启 web 进程后生效
```

注意：npm/pnpm 更新安装根会清掉该目录 — 重新 Copy-Item 即可。插件改动同理（源码在此，部署副本在安装根）。

## 测试

```powershell
# 必须在 dsh 安装根运行（@deepseek-ai/dsh-llm 解析）
node E:\03_Learning\deepseekharness\node_modules\@deepseek-ai\dsh-trellis-breadcrumb\test.mjs
```

## 约定

- DSH 会话跑 trellis 脚本前：`$env:TRELLIS_CONTEXT_ID = "dsh-<session.id>"`（session 文件按此 key 落盘）。
- 会话身份找不到时回退最新 session 文件（单用户场景）。
- 非 Trellis 项目零输出；异常 fail-open。
