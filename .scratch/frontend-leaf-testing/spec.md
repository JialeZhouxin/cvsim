# Spec: 绘图逻辑可测化 + 测试脱钩产品源码（前端 leaf 提取）

> 来源：`/improve-codebase-architecture` 审查（2026-09-03，HTML 报告）遗留摩擦清单 + `/grill-with-docs` 8 问拷问（2026-09-07）。
> 术语见根 `CONTEXT.md`：**leaf 模块**（本次新立）、**Lab schema 组装**、**circuit_v1**。
> 测试策略决策见 `docs/adr/0009-frontend-leaf-testing.md`；架构词汇按 codebase-design。

## 问题（审查确认的事实）

1. **绘图逻辑零测试**：app.js 868 行、0 导出，`buildLut`/`drawHeatmap`/`drawAxes`/`drawScanCurve`/`drawFidSvg`/`renderMatrix`/`fitWignerFrame` 七个绘图函数全部内联副作用，`node --test` 无法驱动。
2. **测试读产品源码**：`test_lab_ui.py:22-30` 用正则从 app.js 抽 `DEFAULT_JSON`（`const DEFAULT_JSON = (\{.*?\});\n`）当请求体；JS 对象字面量 → JSON 转换靠 `_JS_KEYS` 正则白名单（14 个键，硬编码），新增键静默漏转。
3. **死绑定残留**：`editor.js:429` `dom.runBtn` 声明后零引用；`index.html:197` `#state-summary` 无 JS 消费；`fock.js:203/232` 对 `#fock-joint-svg` 双取（裸 querySelector 与 dom 表并存）。

## 已锁定的设计决策（8 问）

| Q | 决策 |
|---|------|
| Q1 | 三工作项同车：绘图纯核提取 + DEFAULT_JSON 搬家 + 死绑定扫尾，一组票据 |
| Q2 | 刀法 = 按关注点分小 leaf：`colormap.js`（LUT+校验+归一化）与 `curve.js`（几何映射+字符串拼接）分开——两个独立变更轴（改配色 vs 改曲线布局） |
| Q3 | 测试技术 = 纯 `node --test`，不引 jsdom/happy-dom/Playwright（离线零依赖是 ADR 级约束）；canvas/svg 落笔不测（ADR-0009） |
| Q4 | DEFAULT_JSON 新家 = 独立 leaf `default_scene.js`；pytest 经 `node --input-type=module` 子进程取值；否决静态 JSON（import attributes 浏览器矩阵 + 异步时序）与后端下发（违反「schema 不含 UI 教学刻度」边界） |
| Q5 | 路由 = `/to-tickets` 四票、票间 `/clear`、逐票 `/implement`（复刻 schema 工作模式） |
| Q6 | pytest 依赖 node = 硬失败给明确文案，不静默 skip、不做 golden JSON 副本（双写反模式） |
| Q7 | ADR-0009 立（难逆转 + 无上下文会困惑 + 真实取舍三判据全中） |
| Q8 | 术语「leaf 模块」入 CONTEXT.md（已落） |

## 范围外（明确不做）

- app.js 改造为导出模块（装配壳地位不动，ADR-0009 决策 1）
- canvas/svg 落笔的视觉回归测试（另立决策）
- `drawHeatmap`/`drawAxes` 整函数搬家（DOM 强耦合规避，见 ADR-0009 理由）
- 死绑定以外的 editor.js 重构

## 验收（spec 口径）

- `node --test`（显式列文件，含新增 colormap/curve 测试）全绿
- pytest 全绿；`test_lab_ui.py` 不再含 `read_text(app.js)` + 正则路径
- app.js 对 DEFAULT_JSON 的引用指向 default_scene.js（字面量本体已搬出）
- `grep runBtn editor.js` 只剩 0 处；`state-summary` 从 index.html 移除或获得消费者（删除）；fock.js 单点获取 joint-svg
- 三后端手工主剧本（vision §5）走通，绘图渲染无回归