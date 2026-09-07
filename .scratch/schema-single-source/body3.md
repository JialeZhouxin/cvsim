## 概述

前端从"手写 schema 知识"切到"消费 `GET /schema`"。票 2 完成后执行。

## 变更

1. **app.js `init()`** 拉 `/schema`,失败显式红条"后端 schema 不可用"(不静默降级,frozen-graph 纪律);无版本协商。
2. **ops.js 运行时合并**:backends/参数形状(name/type/required)/uiName 来自 schema;label/tip/slider 刻度/palette 分组/advanced 留守 ops.js。合并逻辑纯函数化(注入 schema 参数)供 node --test。
3. **editor.js**:`stateFromJson`/`stateFromV1` 的 view/seed/backend 校验改查 schema 边界(消灭两份逐字重复);`toV1Json`/`stateFromV1` 改名逻辑改查 `uiName`(6 张改名表退位)。
4. **initial.js**:名单/下拉选项表从 schema 合并;`remapForBackend` 保持纯函数,名单数据注入。
5. **editor.test.mjs 适配**:合并/序列化函数注入 mock schema fixture(zero-dep 保留)。

## 验收

- [ ] node --test tests/editor.test.mjs tests/fock.test.mjs 全过
- [ ] 手跑 probe:lab_staff / lab_bosonic / lab_undo / lab_scan 全 PASS
- [ ] test_lab_ui.py 过(DEFAULT_JSON 抽取测试可能需适配)
- [ ] 主剧本(vision §5)三后端手走通
- [ ] 前端断网 /schema 失败 → 显式红条,不静默

**Blocks**: 后端切换+删镜像(票 4)
