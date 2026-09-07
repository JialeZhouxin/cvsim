# 票3：default_scene.js — DEFAULT_JSON 搬家，pytest 脱钩正则读源码

## 概述

默认场景 JSON 从 app.js 搬进独立 leaf `cvsim/lab/static/default_scene.js`；`test_lab_ui.py` 删除「正则抽 app.js 源码 + `_JS_KEYS` 白名单转 JSON」整段（测试读产品源码反模式，spec 问题 2）。tracer-bullet 策略：新取值路径先与旧正则解析交叉断言，字节相等后再删旧路。[spec](./spec.md) 票 3/4。

## 变更

1. 新建 `default_scene.js`：`export const DEFAULT_SCENE = { ...原 DEFAULT_JSON 字面量原样迁移... }`；app.js 删除字面量与 `const DEFAULT_JSON`，`import { DEFAULT_SCENE } from "./default_scene.js"`，app.js:743 `defaultScene: DEFAULT_SCENE` 消费点改引用。
2. `tests/test_lab_ui.py` 新增取值函数 `load_default_scene()`（替换旧实现，函数名保留）：
   ```python
   subprocess.run(
       ["node", "--input-type=module", "-e",
        'import { DEFAULT_SCENE } from "./cvsim/lab/static/default_scene.js";'
        'console.log(JSON.stringify(DEFAULT_SCENE))'],
       capture_output=True, text=True, check=True)  # node 缺失 = 硬失败（ADR-0009 决策 4）
   ```
   工作目录 = 仓库根（相对 import 可解析）；stdout strip 后 `json.loads`。**不许静默 skip**：FileNotFoundError/非零返回码 → 带「node 是前端测试链硬依赖，见 CONTEXT.md 环境约定」文案的明确断言失败。
3. 交叉断言护栏（迁移期一次性）：保留旧正则实现为 `_legacy_parse()`，单测断言 `new == legacy`（同一 fixture 上跑新旧两路）。**本票收尾即删 `_legacy_parse` 与 `_JS_KEYS`**——交叉断言跑过一次即完成使命，留双路 = 双写反模式还魂。若最终选择保留护栏而非删除，须在票据 comment 里记录理由并加「勿新增键到 _JS_KEYS」警示，默认答案是删。
4. 显式列文件清单（CONTEXT.md 环境约定行）追加 `default_scene` 相关 node 测试（若本票新增 .test.mjs；纯搬家可仅靠 pytest 交叉断言，不强制新增 node 测试文件）。

## 验收

- [ ] pytest 全绿：`load_default_scene()` 经 node 子进程返回与旧正则路径逐键相等的场景对象
- [ ] `grep -n "DEFAULT_JSON" cvsim/lab/static/app.js` → 0 处；`grep -n "_JS_KEYS\|read_text.*app.js" tests/test_lab_ui.py` → 0 处
- [ ] app.js 加载后默认场景行为不变（手工：启动 Lab 页面，默认双真空模 + 位移器场景照常渲染）
- [ ] node 缺失时 pytest 明确红 + 文案指引（可用 `PATH= python` 式验证一次）

**Blocks**: 无