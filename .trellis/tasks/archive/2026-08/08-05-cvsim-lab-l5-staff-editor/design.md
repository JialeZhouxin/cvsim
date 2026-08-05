# Gaussian Lab L5 — Design（五线谱编辑器）

## 1. 架构边界

```
┌─ Browser SPA ─────────────────────────────────────┐
│ staff.js (新): 五线谱渲染 + DnD + 放置状态机       │
│ editor.js (改): state 扩展 ui.x + 排序重排         │
│ ops.js (改): 源重构（vacuum 加入 / tmsv 移除）     │
│ app.js (改): scan 联动 + 托盘图标化 + JSON 折叠    │
│ style.css/tokens.css (改): 轨道/门块/浮层样式      │
└───────────────┬───────────────────────────────────┘
                │ POST /run（不变）        POST /scan（不变）
┌───────────────▼───────────────────────────────────┐
│ server.py / ir.py — 零改动                        │
└───────────────────────────────────────────────────┘
```

## 2. 数据模型扩展（前端 state 内）

```js
// node 新增（仅前端构建时附加，toCircuitJson 输出 ui 字段）
{ id, op, params, mode?, modes?, ui: { x: float } }
// ui.x = 水平位置（渲染 + 排序键）；载入 JSON 无 ui.x → 按数组索引赋 x
// 排序键 = (x, modeKey)：modeKey = single→mode, two→modes[0], source→-Infinity
```

- `sortNodes(nodes)`：稳定排序；source 恒排最前（源无 x，x=-∞）
- `toCircuitJson`：节点带 `ui: {x}` 输出（schema `ui` 字段已是自由对象，后端忽略）

## 3. 放置状态机（editor state）

```js
placing: null | { op, kind, modeA: int }   // 双模门"待选第二模"态
```

- `dragover 轨道 A`（single）→ 落定 `{mode:A, ui.x}`
- `dragover 轨道 A`（two）→ `placing={op, modeA:A}`，门半透明预览在 A，轨道 A `.arm` 高亮，状态条"选择第二个模式"
- `placing` 期间 `click 轨道 B`：B===A → 拒绝提示保持态；B!==A → 落定 `modes=[A,B]`，清 placing
- `Esc` / 点画布空白 → 清 placing（丢弃）
- 双模守卫：`sourceModes(nodes) < 2` → 拒绝 + 状态条提示（沿用）

## 4. 五线谱 DOM 结构

```html
<div class="staff" id="staff">              <!-- 双向滚动容器 -->
  <div class="staff__grid">                 <!-- 宽度 = max(x)+1 格 -->
    <div class="staff__row" data-mode="0">  <!-- 每模一行 -->
      <div class="staff__source">相干态 α=1</div>   <!-- 左端源标记 -->
      <div class="staff__lane"></div>               <!-- 放置区（DnD target）-->
      <div class="gate" data-id="n3">相位 φ</div>   <!-- 门块（绝对定位按 x）-->
    </div>
    ...
  </div>
</div>
```

- 门块绝对定位：`left = x * GATE_W`；行内高度 100%
- 双模门：跨两行渲染（`gridRow: span 2` 或覆盖两行的绝对块），视觉 = 竖直方块
- 渲染全量重绘（m ≤ 8、门 ≤ 几十，无性能问题，沿用 renderRows 全量替换风格）

## 5. 参数浮层

```html
<div class="gate-card" data-id="n3">  <!-- 绝对定位在门块上方 -->
  标题 / mode 信息（只读）/ 滑块+数字（复用现有 param 控件样式）
</div>
```

- 打开：点击门块；关闭：Esc / 点击浮层外
- 滑块 input → 实时 updateParam + renderJson + emit（沿用现有热路径）
- 打开时若该 op 有 `sweep` 参数 → 调 `hooks.onPickSweep(id)` → app.js 同步 scan 下拉

## 6. 源渲染

- 行序 = mode 升序；`coherent` 源 → 其 1 行左端圆点标记（点击弹浮层编辑 α）
- `vacuum` 源（可 nmode>1）→ 连续 n 行左端"真空"标签；点击无参数（浮层只显示说明或隐藏）
- `tmsv`（仅旧 JSON 载入）→ 2 行左端共用标记框 `TMSV(r=…)`，点击浮层编辑 r
- 删源：确认弹窗（`confirm()` 或自定义）+ 连带删除该源贡献行上的所有门

## 7. 源贡献 → 行映射

```js
// 顺序遍历 nodes 中 source，累计模数：coherent/vacuum→+1（vacuum nmode 视为 1 行/次? ）
```

- **vacuum nmode 语义**：palette 每次加 `vacuum` 固定 `nmode=1`（+1 模）；JSON 里手写 nmode>1 的 vacuum → 渲染 n 行，删源连带 n 行
- 行与源的关系：每行记录其源节点 id（渲染时从 source 序列推导，纯函数可测）

## 8. 滚动与布局

- `.staff { overflow: auto }` 占电路面板主体；`.staff__grid` min-width = 源列宽 + 门区
- 轨道行高 56px；门格 GATE_W=72px；源列宽 ~110px（含源标记）
- 托盘图标化：卡片窄化（label 缩短/图标），面板宽 ~160px

## 9. 模块与测试

| 模块 | 职责 | 测试 |
|------|------|------|
| `ops.js` | vacuum 加入 OPS、tmsv 移除、`sortNodes`、`placeNode`（放置状态机纯函数） | node --test |
| `staff.js`（新） | 五线谱 DOM 渲染 + DnD 事件 + 浮层 | 渲染逻辑纯函数抽离，node --test |
| `editor.js` | state 管理 + JSON 同步（沿用）+ 浮层桥接 | 现有测试迁移 |
| `app.js` | scan 联动 + 托盘图标化 | —（headless CDP） |

- 放置状态机、排序、源→行映射必须纯函数（ESM 导出），node --test 覆盖
- headless CDP（L4 复用脚本）：五线谱渲染、双模两步放置、折叠 JSON 区、扫参联动

## 10. 兼容

- 旧 JSON 无 `ui` → x 按数组索引；`tmsv` 源仍渲染可运行（连带删除规则同源）
- 保存输出带 `ui.x`；后端 ignore ui 字段（已实证）
- schema/后端零改动；vision §4 白名单 amend（vacuum 入托盘、tmsv 出托盘）+ changelog
