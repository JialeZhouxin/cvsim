# ADR-0009: 前端逻辑测试 = 纯 leaf 模块 + node --test，禁 DOM 伪造库

## 状态

Accepted（2026-09-07，/grill-with-docs 拷问后定案）

## 背景

app.js 868 行、0 导出，七个绘图函数（buildLut/drawHeatmap/drawAxes/drawScanCurve/drawFidSvg/renderMatrix/fitWignerFrame）全部内联副作用，无自动化测试；`test_lab_ui.py` 用正则从 app.js 源码抽 `DEFAULT_JSON` 当请求体（JS 对象字面量转 JSON 的键白名单 `_JS_KEYS` 手写 14 个键，新增键静默漏转）。request.js（ADR 之外的先例）已证明 leaf 模式可行：零 import、零 DOM、环境注入、`node --test` 直测。本仓库离线零依赖是 ADR 级约束（无 package.json、无 node_modules）。

## 决策

1. 前端逻辑的可测单元一律走 **leaf 模块**：零 import、零 DOM、环境依赖由调用方注入，`node --test` 直测（术语见 CONTEXT.md「leaf 模块」）。app.js 保持装配壳角色、0 导出，不因可测性改造导出面。
2. 绘图函数拆出**纯核**（LUT 构建、网格校验、对称归一化、坐标映射、polyline/path 字符串拼接）进 leaf 模块测试；**canvas/svg 落笔**不测，靠现有 probe 脚本 + 人工。
3. **不引入 jsdom/happy-dom/Playwright**：伪造 DOM 或真浏览器都是第一份 node 依赖，违反离线约束；纯核测住的是逻辑，落笔只是搬运。
4. 测试链的 node 依赖**硬失败不静默 skip**：pytest 侧经 `node --input-type=module` 子进程取前端数据（default_scene）时，node 缺失 = 明确报错，不做 golden JSON 副本兜底（那是刚消灭的双写反模式）。

## 理由（取舍）

- 纯 node --test（a）vs jsdom 伪造 DOM（b）vs Playwright 截图（c）：(b)(c) 都给零依赖仓库引入 node_modules，且把测试面从逻辑扩到搬运代码——脆、慢、违离线；(a) 与 request.js 先例同构，测的是真逻辑（几何映射、归一化、校验），落笔像素不是知识。
- 纯核剥离 vs 整函数搬家：drawHeatmap/drawAxes 的 DOM 部分强耦合视口与 getComputedStyle，硬搬只会造出需要伪造环境的假 leaf；切纯核后每个函数剩下的 DOM 汇点 ≤ 一个。
- 硬失败 vs golden JSON：node 已是前端测试链硬依赖（CONTEXT.md 环境约定），dev/CI 皆有；副本兜底制造第二知识源 + tripwire，正是本轮要消灭的模式。

## 后果

- 每个绘图纯核有 `node --test` 直测；app.js 继续无导出，测试不经它。
- 新前端逻辑默认问一句「能不能写成 leaf」；答不了（强 DOM 耦合）时诚实承认不测落笔。
- pytest 对 node 的调用是 python 测试链第一次硬依赖 node，环境约定同步记录。
- 若未来真需要视觉回归（落笔层），另立决策，不在本 ADR 的纯核范畴内。