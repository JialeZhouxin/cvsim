# Review: Lab 前端渲染性能 / 布局抖动

**审查范围**: `cvsim/lab/static/`（17 个文件：`app.js` 837 行 / `editor.js` 767 行 /
`staff.js` 388 行 / `fock.js` 382 行 / `ops.js` 442 行 / `style.css` 1347 行 / +
`colormap.js` `curve.js` `svg_kit.js` `steps_slider.js` `request.js` `schema_store.js`
`initial.js` `ops_schema.js` `scan_form.js` `default_scene.js` `index.html` `tokens.css`）

**基线**: `c583d78`（2026-09-15）。审查时该状态下 Wigner frame 修复尚为**未提交的
工作区改动**，现已经由 `d997fa4` 落盘；`docs` 提交 `ae3a1dc` 是当前 HEAD。
本文所有 `file:line` 锚点对应**已提交的 `ae3a1dc`（工作区内容与审查时一致）**。
**日期**: 2026-09-17
**方法**: 静态代码审查（读-写交错、强制同步布局、重复计算、DOM 重建范围）
**未做**: 未跑浏览器 profile、未跑 CDP `Performance` 域计数。本文所有结论是**源码级推理**，
每条都给了 `file:line` 证据与可验证的断言，但**没有实测毫秒数**。§7 给出量化方案。

**本次未改任何代码。**

---

## §1 结论摘要

卡顿的主因不是"某个函数慢"，而是**三条交互路径（滑条 / 拖拽 / resize）每次事件都
触发了全工作台范围的重建或强制同步布局**：

| 优先级 | 问题 | 触发频率 | 单次代价 |
|--------|------|----------|----------|
| P0-1 | fock `cutoff` 滑条 → 全量 `render()`（staff + palette + JSON 全重建） | ~60–120/s | 数百 DOM 节点重建 |
| P0-2 | 任何 gate 参数滑条 → `onState` → `refreshScanNodes` + `fitWignerFrame`（强制 layout） | ~60–120/s | 1 次强制 layout + 3 个 select 重建 |
| P0-3 | canvas `ResizeObserver` → `drawHeatmap` 全量重算（含 O(n²) 单元映射） | resize 期间多轮 | n² 次运算 + 1MB 分配 + 1024² drawImage |
| P0-4 | `dragover` 每事件读 rect → 写 `scrollTop` → 读 rect → 写 style（读-写交错） | ~60/s | 每事件 2+ 次强制 layout |
| P0-5 | bosonic 分步滑条 → 每 input 全量 `drawHeatmap` + `drawAxes` | 高于帧率 | 同 P0-3 |
| P1 | `fitWignerFrame` 是抖动的**结构根因**，7 个调用点 × 每次 style recalc + rect 读 | 全渲染路径 | 应结构性删除（§3.6） |
| P2 | `*{scrollbar-*}`、`aria-live` 挂在每编辑重建的 `#staff`、colorbar 静态像素重画 | — | 低 |

**最关键的一条**：P0-1 与 P0-2 都源于同一个结构性事实——`editor.js render()`
（`editor.js:403-412`）是一个**无差别全量重渲染**函数，任何状态变化都走它，而
`app.js` 的 `onState` 钩子（`app.js:714`）又在它内部做了昂贵的副作用。项目里已经有
正确的先例：`setInitial`（`editor.js:593-604`）只走 `renderJson() + onState + emit`，
**不碰 staff 与 palette**。修法即把滑条类路径对齐到这个先例。

---

## §2 P0 · 交互路径（用户直接可感的卡顿）

### §2.1 【P0-1】fock `cutoff` 滑条每 `input` 重建整个工作台 DOM

**位置**: `fock.js:347-355` → `editor.js:749-754`（`setCircuit`）→ `editor.js:403-412`（`render`）

```js
// fock.js:347
dom.cutoffSlider?.addEventListener("input", () => {
  const nm = nmodeOfState();
  const cut = Array(nm).fill(Number(dom.cutoffSlider.value));
  hooks.setCircuit({ cutoffs: cut, initial: clampInitial(...) });
  dom.cutoffVal.textContent = String(dom.cutoffSlider.value);
});
```

`setCircuit`（`editor.js:749-754`）调 `render()`，而 `render()` 依次执行：

1. `staff.render()`（`editor.js:404`）→ `staff.js:81` `root.replaceChildren()`，然后重建
   全部 mode row + lane + mode-del 按钮 + 全部 gate 块 + gate-del 按钮，
   并在新 grid 上重挂 4 个委托监听（`staff.js:185/231/234/257`）；
2. `renderPalette()`（`editor.js:405`）→ `editor.js:505-556` `dom.palette.replaceChildren()`
   + 全部 group/`<details>`/item 重建（每 item 3 个监听），托盘实际**只依赖
   `state.backend`**；
3. `renderJson()`（`editor.js:406`）→ `JSON.stringify(toV1Json(state), null, 2)`
   写入 `#json-input`，**即使 JSON 折叠面板是关闭的**；
4. `renderFockControls()`（`editor.js:407`）；
5. `hooks.onState(state)`（`editor.js:408`）→ 见 §2.2；
6. `emit(toV1Json(state))`（`editor.js:411`）→ 第二次 `toV1Json`。

滑条 `input` 在拖动时约 60–120 次/秒。此外 `staff.render()` 开头 `closeCard()`
（`staff.js:77`）会**顺手关掉打开的参数卡片**——即拖动 cutoff 会把用户正在看的
gate 参数卡片弹掉，这是与性能同源的行为耦合。

**修法**（对齐 `setInitial` 先例）: cutoff 变化只影响 `cutoffs`/`initial` 字段，
不改变 staff 几何与托盘内容。改为

```js
state = { ...state, ...patch };
renderJson();
hooks.onState(state);
emit(toV1Json(state));
```

即 `setCircuit` 不复用 `render()`；若担心 `renderFockControls` 里的
`syncFockInputValues()`（`editor.js:694-704`）遗漏，单独调它。

**验证断言**: 拖 cutoff 滑条时 `staff.render()` 与 `renderPalette()` 的调用次数为 0。

---

### §2.2 【P0-2】任何 gate 参数滑条 → 强制同步布局 + 3 个 select 重建

**位置**: `staff.js:362`（`range.addEventListener("input", ...)`）→ `editor.js:481-487`
（`onParam`）→ `app.js:714`（`onState` 钩子）→ `app.js:529-544` + `app.js:442-447`

```js
// editor.js:481
onParam: (id, key, value) => {
  pushHistory();
  state = { ...state, nodes: state.nodes.map(...) };
  renderJson();
  hooks.onState(state);   // ← 这里
  emit(toV1Json(state));
},
```

```js
// app.js:714
onState: (state) => { refreshScanNodes(); syncBackendPanels(state.backend); },
```

`refreshScanNodes()`（`app.js:529-544`）`replaceChildren()` 三个 `<select>`
（`scanNode` / `scanParam` / `scanModesA`）并重建全部 `<option>`——但拖动参数
**不改变节点集合**，这些 select 的选项是稳定的。

`syncBackendPanels()`（`app.js:442-447`）写入 7 个面板的 `hidden`，**然后**
`fitWignerFrame()`（`app.js:446`）。`fitWignerFrame`（`app.js:46-58`）内部：

```js
const gap = parseFloat(getComputedStyle(wignerBox).gap || "16");  // 48  读
const availW = wignerColorbar.getBoundingClientRect().left          // 49  读
  - wignerBox.getBoundingClientRect().left - gap;                  // 50  读
const h = wignerBox.clientHeight;                                  // 51  读
const s = window.matchMedia("(min-width: 80rem)").matches ...      // 53  读
wignerFrame.style.width = s + "px";                                // 56  写
wignerFrame.style.height = s + "px";                               // 57  写
```

序列是 **写 `hidden` ×7 → 读 layout（强制同步 reflow）→ 写 style**，一次滑条
input 完成一整个 layout thrash 周期。额外的代价：`window.matchMedia()`
（`app.js:53`）每次调用都**新建一个 `MediaQueryList` 对象**，而它有 8 个调用点
（`app.js:127/216/221/222/260/265/284/446`）。

**修法**:
1. `onParam` 路径不做 `refreshScanNodes()`——加脏键（`nodes` 引用 + `backend` 未变则
   早退），或把 `onState` 拆成 `onNodesChanged` / `onBackendChanged` 两个钩子；
2. `syncBackendPanels` 在 backend 未变时整体早退（含末尾的 `fitWignerFrame()`）；
3. `fitWignerFrame` 里的 `matchMedia` 提升为模块级单例（`addEventListener("change", fitWignerFrame)`
   替代每次查询）。

**验证断言**: 拖参数滑条时 `getBoundingClientRect` / `getComputedStyle` / `matchMedia`
调用次数为 0。

---

### §2.3 【P0-3】canvas `ResizeObserver` 触发整张热图重算

**位置**: `app.js:210-213` → `drawHeatmap`（`app.js:111-160`）

```js
new ResizeObserver(() => {
  if (lastWigner) drawHeatmap(lastWigner.W);
  drawAxes(lastLim);
}).observe(canvas);
```

`drawHeatmap` 每次都做：

- `validateWignerGrid(W)`（`app.js:112`）→ `colormap.js:34-40`，`W.some(row => row.some(...))`，
  **n² 次有限性检查**；
- **新建**离屏 canvas（`app.js:115-118` `createElement` + `getContext`）；
- `wignerScale(W)`（`app.js:120`）→ `colormap.js:44-48`，**第二遍 n² 扫描**；
- `octx.createImageData(n, n)`（`app.js:128`）→ n=512 时 **1 MB** `Uint8ClampedArray`；
- `app.js:129-138` 逐格 `wignerT` + 3 次 LUT 查表 → **第三遍 n²**；
- `octx.putImageData(img, 0, 0)`（`app.js:139`）；
- `canvas.width = pw; canvas.height = ph;`（`app.js:146-147`）**无条件赋值**——
  即使值未变，按 HTML 规范设置 `canvas.width` 也会重置位图与上下文状态；
- `ctx.imageSmoothingQuality = "high"`（`app.js:151`）+ `drawImage` 到 1024²
  （`app.js:152`）——从 n=64 放大到 1024 是 16× 双三次上采样，每次 resize 都付。

而 resize 期间这条链会**跑多轮**：`wignerBox` 的 RO（`app.js:216`）与
colorbar/side 的 RO（`app.js:221-222`）调 `fitWignerFrame` 改 frame 尺寸 →
canvas 的 `clientWidth` 变 → canvas 的 RO 回调再全算一遍。等于每次 resize
至少两遍完整热图重建。

**修法**:
1. 离屏 canvas 缓存为模块级单例，`W` 引用未变则**跳过整个 `createImageData` 段**，
   只重做 `drawImage` blit；
2. `if (canvas.width !== pw) canvas.width = pw;`（`app.js:146-147` 同理）；
3. 三个 RO 回调（canvas / wignerBox / colorbar / side）统一用 `requestAnimationFrame`
   合并到一帧一次；
4. `validateWignerGrid` 与 `wignerScale` 融进同一个 n² 遍历（三次 → 一次）；
5. `imageSmoothingQuality` 从 `"high"` 降到 `"medium"`（视觉差异在 16× 放大下不可辨，
   代价显著）。

**验证断言**: 同 `W` 连续两次 `drawHeatmap`，`createImageData` 调用次数为 1。

---

### §2.4 【P0-4】`dragover` 每事件强制布局 + 全子树查询

**位置**: `staff.js:185-230`

```js
grid.addEventListener("dragover", (e) => {
  ...
  const rr = root.getBoundingClientRect();      // 189  读
  if (e.clientY < rr.top + 56) root.scrollTop -= 14;   // 190-191  写（改滚动 → 失效）
  else if (e.clientY > rr.bottom - 56) root.scrollTop += 14;
  ...
  const gridRect = grid.getBoundingClientRect();       // 194  读（同一事件内又一次强制布局）
  const x = Math.max(0, Math.round((e.clientX - gridRect.left - MODE_W) / GATE_W));
  ...
  root.querySelectorAll(".staff__lane--hover, .staff__lane--conflict")
      .forEach((el) => el.classList.remove(...));      // 214-216  全子树查询
  lane.classList.add(conflict ? "..." : "...");        // 219  写 class
  ghostEl.style.left = `${...}px`;                     // 228  写（触发 layout）
  ghostEl.style.top = `${...}px`;                      // 229  写（触发 layout）
});
```

`dragover` 在拖动期间约 60 次/秒，每次 2 次 `getBoundingClientRect` + 1 次全子树
`querySelectorAll`，且读-写交错（189 读 → 191 写 → 194 读）。`gridRect` 在拖动期间
是**不变**的，但每次重算。

**修法**:
1. `rr` / `gridRect` 缓存到 `dragstart`，在 `root` 滚动或 window resize 时失效；
2. 记 `let prevLane = null` 替代 `querySelectorAll`（只需清上一格）；
3. 自动滚动放进 `requestAnimationFrame`，一帧最多滚一次；
4. ghost 用 `transform: translate(x, y)` 替代 `left`/`top`——`transform` 走合成，
   不触发 layout/paint。

**验证断言**: 连续 10 次 `dragover` 事件，`getBoundingClientRect` 调用次数 ≤ 1（缓存后）。

---

### §2.5 【P0-5】bosonic 分步滑条每 `input` 全量重绘

**位置**: `app.js:340-367`

```js
const show = (k) => {
  ...
  if (s.wigner) drawWignerResult({ wigner: s.wigner });   // 363
};
slider.oninput = () => show(slider.value);                // 365
```

`drawWignerResult`（`app.js:288-308`）→ `drawHeatmap` + `drawAxes`。`input` 事件
速率高于显示帧率，未节流。同样受益于 §2.3 的离屏缓存。

**修法**: `oninput` 内用 rAF 节流（只保留最新 `k`）+ 复用离屏缓存。

---

## §3 P1 · 重复劳动与结构问题

### §3.1 【P1-6】`fitWignerFrame` 是抖动的结构性根因，应设法删除

**位置**: `app.js:46-58`；调用点 8 处：`app.js:127`（`drawHeatmap` 内）、`216`、
`221`、`222`（三个 RO）、`260`（fock 路径）、`265`（bosonic 路径）、`284`
（gaussian 路径）、`446`（`syncBackendPanels`）。

这是一个**用 JS 在解 CSS 循环依赖**：frame 边长 = `min(可用宽, 可用高)`，而"可用宽"
取决于 colorbar 列（`auto` 轨道，宽由刻度标签内容决定）与侧列（宽由 meters / r̄ 表
内容决定），后两者又受 frame 挤压。项目已为它写了 **3 个源码顺序回归测试**
（`tests/test_lab_ui.py:130-253`：`test_wigner_frame_fit_contract` /
`test_wigner_fit_runs_after_colorbar_labels` / `test_wigner_fit_runs_after_side_panel_render`）
——这些测试的存在本身就是循环复杂度的证据。

**修法方向**（需一次性验证，非逐条修补）:
- `≥80rem` 三列布局：`.wigner` 的高度已由 flex 确定（非内容驱动）→ 可设
  `container-type: size`，frame 用 `width: min(100cqw, 100cqh); height: same;
  aspect-ratio: 1`。原注释里"container-type 高度塌缩"的问题只在**页面流**布局下成立。
- `<80rem` 单列页面流：`width: 100%; aspect-ratio: 1`，CSS 原生。
- 完成后可删除：`fitWignerFrame` 函数 + 3 个 `fitWignerFrame` 的 RO
  （`app.js:216/221/222`）+ 3 个顺序测试。
- colorbar 刻度标签宽度仍是 `auto` 轨道 → 若仍想避免循环，把 colorbar 列改为
  **固定宽度**（`minmax(2.5rem, auto)` 或显式宽度）即可彻底断开依赖。

这是收益最大的一条：删掉一整类问题，而不是优化它。

### §3.2 【P1-7】colorbar 每次重画 128 次 `fillRect` + 字符串拼接

**位置**: `app.js:154-159`

```js
for (let k = 0; k < 128; k++) {
  const t = Math.round((k / 127) * 255);
  cb.fillStyle = `rgb(${LUT[t * 3]},${LUT[t * 3 + 1]},${LUT[t * 3 + 2]})`;
  cb.fillRect(0, 127 - k, 8, 1);
}
```

`LUT` 是模块常量（`app.js:22` `const LUT = buildLut()`），**colorbar 的像素永不变化**。
每次 `drawHeatmap` 都在重画同一张渐变图：128 次 `fillStyle` 字符串拼接 + 128 次
`fillRect`。

**修法**: 移到模块初始化时画一次；或直接删掉 canvas 换成 CSS
`linear-gradient`（零 JS，且能跟随 `--color-*` 主题变量）。

### §3.3 【P1-8】离屏 canvas 每次新建

**位置**: `app.js:115-118`。`document.createElement("canvas")` + `getContext("2d")`
每次 `drawHeatmap` 都执行，未复用。与 §2.3 同一处修法。

### §3.4 【P1-9】`canvas.width/height` 无条件赋值

**位置**: `app.js:146-147`。见 §2.3 第 2 点。同值赋值也会重置位图/上下文，是常见的
隐性开销。

### §3.5 【P1-10】`getComputedStyle` 重复调用 / CSS 变量重复解析

| 位置 | 次数 | 说明 |
|------|------|------|
| `app.js:177`（`drawAxes`） | 1/次 | 取 `--color-axis` `--color-paper`（`178-180`） |
| `app.js:48`（`fitWignerFrame`） | 1/次调用 | 只为取 `gap`——可改读 CSS 变量常量 |
| `app.js:618`（`drawScanCurve`） | 1/次 | 取 `--color-rule` `--color-ink` `--color-accent`（`619-621`） |
| `fock.js:118-120`（`cssVar`） | — | `drawBars` 调 **4 次**（`fock.js:126-129`），`drawJointPair` 调 **2 次**（`195-196`） |

每次 `getComputedStyle` 都是一次样式解析入口；`fock.js` 的 `cssVar` 每次调用都
重新取 `document.documentElement` 的 computed style。

**修法**: 抽一个 `readThemeVars([...names])` 单点，一次 `getComputedStyle` 读全部；
或在 `MatchMedia("(prefers-color-scheme)")` / 主题变更时缓存失效。项目已有
`--color-*` 主题层（`tokens.css`），缓存是安全的。

### §3.6 【P1-11】`toV1Json` 在节点循环内调用 `renames()`

**位置**: `ops.js:389-414`，关键行 `ops.js:394`

```js
for (const n of state.nodes) {
  const R = renames();     // ← 每节点一次
  ...
}
```

`renames()`（`ops.js:374-378`）每次调 `schemaTables()` 并**展开 3 个对象**
（`{...s.uiToOp, ...}`）。节点数为 k 时做 k 次。应提到循环外（每次 `toV1Json`
一次）。

### §3.7 【P1-12】单次 mutation 序列里 `toV1Json` 被调两次

**位置**: `editor.js:399`（`renderJson`）与 `editor.js:411`（`emit`）——`render()` 内；
另外 `editor.js:484-486`（`onParam`）与 `editor.js:601-603`（`setInitial`）也是
`renderJson()` + `emit()` 各算一次。

`toV1Json` 是 O(节点数) 的对象构造 + 字符串化。修法：算一次，两处共用。

### §3.8 【P1-13】`renderPalette()` 每次 `render()` 全量重建

**位置**: `editor.js:405` 调用；`editor.js:505-556` 实现。托盘内容**只依赖
`state.backend`**（`opsForBackend(state.backend)`，`editor.js:508`）。

项目里已有正确的缓存范式：`editor.js:656-660` 用
`dom.initialInputs.dataset.nmode`（`initialCacheKey`）早退。照抄即可：

```js
if (dom.palette.dataset.backend === state.backend) return;
dom.palette.dataset.backend = state.backend;
```

### §3.9 【P1-14】`setView` → 全量 `render()`

**位置**: `editor.js:745-748`；调用点 `app.js:784-787`（mode select 的 `change`）。

```js
setView: (patch) => {
  state = { ...state, view: { ...state.view, ...patch } };
  render();   // 重建 staff + palette，但 view 只影响 Wigner 与 JSON
},
```

切换 Wigner mode 时，staff 几何与托盘内容都不变。应走
`renderJson() + onState + emit`。

### §3.10 【P1-15】joint 热图每格一个 `<rect>`，每次 render 全量重建

**位置**: `fock.js:175-187`（`drawHeat`）

```js
for (const c of cells) {
  svg.append(el("rect", { x: c.j, y: c.i, width: 1, height: 1, fill: color,
    "fill-opacity": ... }));   // 每格 6 次 setAttribute
}
```

`overlayHeat`（`fock.js:53-68`）产出 `rows × cols` 个 cell，**前端无上限**——
上限来自后端 cutoff 上界 30（`cvsim/lab/schema.py:139`
`"cutoff": {"min": 1, "max": 30}`，经 `/schema` 下发），故 joint 网格最大
30×30 = **900 格**，即 900 个 `<rect>` × 6 次 `setAttribute`。
`drawHeat` 开头 `svg.replaceChildren()`（`fock.js:178`）
每次全部丢弃重建。且 `renderBatch`（`fock.js:379`）会再触发一轮 `drawJointPair`
→ `drawHeat`（采样侧），`renderDist`（`fock.js:378`）也重绘柱状图。

**修法**: 持久化 rect 节点数组，只改 `fill-opacity`（值未变则跳过）；或改用单个
`<path>` / 一个 canvas + `ImageData`（与 `drawHeatmap` 同一套写法，项目已有先例）。

**注**: `drawBars`（`fock.js:123-172`）每根柱 2 个 `<rect>` + 可选 `<text>`，
最多 30 柱 = ~60–90 元素，同样每次重建，但规模小于热图。

### §3.11 【P1-16】`drawFidSvg` 用 `svg.innerHTML`

**位置**: `app.js:392-396`。在 SVG 命名空间元素上写 `innerHTML` 会走 HTML 解析器
路径（外来内容），比 `replaceChildren` + `el()` 慢，且与项目其余 SVG 绘制风格
（`svg_kit.el`）不一致。

### §3.12 【P1-17】`drawAxes` 每次全量重建 ~15 个元素

**位置**: `app.js:169-208`：`svg.replaceChildren()`（`175`）+ 2 条主线 + 5 条刻度线
+ 8 个 `<text>` ≈ 15 个元素，每个经 `el()` 逐属性 `setAttribute`。
低优先（每次 resize/热图重绘才走），但可复用节点只改属性。

---

## §4 P2 · CSS 与杂项

### §4.1 【P2-18】`* { scrollbar-width; scrollbar-color }`

**位置**: `style.css:1322-1325`

```css
* {
  scrollbar-width: thin;
  scrollbar-color: var(--color-rule) transparent;
}
```

这两个属性**都是可继承属性**，`*` 选择器让规则命中整棵 DOM 树（每次样式重算都要
匹配全部元素）。改为 `:root` 即可，继承会自动下发到所有后代。

### §4.2 【P2-19】`aria-live="polite"` 挂在每编辑全量重建的 `#staff`

**位置**: `index.html:59`

```html
<div id="staff" class="staff" aria-live="polite" aria-label="五线谱电路编辑区"></div>
```

`#staff` 的子树上任何编辑都走 `replaceChildren()` 全量重建（`staff.js:81`），
对一个 live region 反复重建会让 a11y 树反复 diff 并产生播报噪音。而状态播报已由
`#status`（`index.html:219`，`role="status" aria-live="polite"`）承担，
`setStatus`（`app.js:82-85`）是唯一的播报口。

**修法**: 从 `#staff` 移除 `aria-live`。

### §4.3 【P2-20】`scrollIntoView` 紧跟 DOM 写入 → 强制 layout flush

**位置**: `app.js:479`（`showMeasurement`）、`app.js:676`（`doScan` 成功回调）。

```js
measurementPanel.hidden = false;
measurementPanel.scrollIntoView({ block: "nearest" });   // 立即读布局
```

各一次/操作，频率低，但属同一类抖动。可放进 rAF。

### §4.4 【P2-21】`init()` 串行 `await`

**位置**: `app.js:795`（`fetch("/schema")`）与 `app.js:816`（`fetch("/health")`）。

`/health` 只用来填版本号（`app.js:817`），**不参与 `schemaOk` 门控**。串行使首个
`editor.render()`（`app.js:821`）多等一个 RTT。改 `Promise.all` 或让 `/health`
后置不阻塞。

### §4.5 【P2-22】不要加 `contain` / `content-visibility`

隐藏面板已经零布局成本：`[hidden] { display: none !important }`（`style.css:20-22`）
+ `.fold:not([open]) > * { display: none }`（`style.css:82-84`）。这条是**反向记录**：
避免后续优化时误加 `contain` / `content-visibility` 引入新的容器/滚动副作用。

---

## §5 已经做对的（审查中确认，勿回退）

| 机制 | 位置 | 为什么重要 |
|------|------|-----------|
| seq guard + 引用计数 busy | `request.js:21-39`、`app.js:453-463` | 过期请求静默丢弃、busy 计数不串台（曾修控件卡死） |
| run debounce 120ms | `app.js:522-526` | 参数拖动只在停手后发一次请求——**这层已经对了**，卡顿来自它之外的同步 DOM 工作 |
| 拖拽期抑制 emit | `editor.js:362`（声明）、`editor.js:490-495`（gate 拖动）、`editor.js:536-549`（托盘拖动） | 拖动中不逐帧发请求，drop/取消后单次 |
| `onParam` 不调 `staff.render()` | `editor.js:481-487` | 有意为之——重建 DOM 会中断 range 拖动 |
| 用引用比较的不可变历史 | `editor.js:315-338` | 每步 O(1)，无深拷贝 |
| `.wigner__side` 用 `max-width` 而非 `minmax` 轨道 | `style.css:343-357`，测试锁定 `test_lab_ui.py:214-253` | `minmax` 会把轨道钉到 max，内容窄时仍挤压缩 frame |
| 零外部资源 | `test_lab_ui.py:108-116` 锁定 | 本地工作台硬约束 |
| 无 `backdrop-filter` / 无 `filter` / 无非合成动画 | 全 CSS 扫描 | 无整层重绘源；`transition` 只作用于 `background-color`/`color`/`transform`/`opacity` |

---

## §6 建议落地批次

**批次 1（吃掉大部分可感卡顿）**: §2.1 → §2.2 → §2.3。
三条都在既有函数的调用序/缓存层，不改架构，风险低。

**批次 2（删掉整类问题）**: §3.1。需一次性几何验证（跑
`tests/lab_wigner_layout_probe.mjs` 的 1440/1280/1920 × gaussian/bosonic/fock 矩阵），
完成后可连带删除 3 个源码顺序测试与 3 个 RO。

**批次 3（重复劳动清理）**: §3.2 §3.6 §3.7 §3.8 §3.9 §3.10。

**批次 4（CSS / 杂项）**: §4.1 §4.2 §4.4。

每批次独立可验证，不互相阻塞。

---

## §7 量化验证方案（**尚未执行**）

`tests/lab_wigner_layout_probe.mjs:40-80` 已有可直接复用的零依赖骨架：
Node ≥22 原生 `fetch` + `WebSocket`、headless Edge（
`C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe`）、CDP `send()` /
`evalJs()`。建议新增 `tests/lab_render_perf_probe.mjs`：

1. `Performance.enable` + `Performance.getMetrics`，读 `LayoutCount` /
   `RecalcStyleCount` / `LayoutDuration` / `RecalcStyleDuration`；
2. 用 `Input.dispatchMouseEvent` 或直接 `evalJs` 派发合成 `input` 事件序列
   （cutoff 滑条 100 步 / 参数 range 100 步 / 20 次 `dragover`）；
3. 断言：修复后 `LayoutCount` 增量显著低于基线（建议先跑基线，把**实测值**写回本文，
   替换 §1 的定性判断）。

**注意**（诚实边界）: 本文未跑该 probe，因此 §2 的"频率 ~60–120/s"是事件模型推算
（`input` / `dragover` 的浏览器派发速率），**不是实测**。§2 各条的"验证断言"是
可直接写进 probe 的判据。

---

## §8 未覆盖 / 未验证

- **未做浏览器 profile**：无 flame chart、无 `Performance` 域计数、无 React-DevTools
  类渲染耗时归因。所有代价排序基于 DOM 操作数 × 事件频率的推理。
- **未验证 `ResizeObserver` 循环告警**：`wignerBox` 的 RO（`app.js:216`）回调写
  frame 尺寸，理论上可能改变 `wignerBox` 的 border-box 触发再入
  （"ResizeObserver loop completed with undelivered notifications"）。
  `test_lab_ui.py:183-192` 的注释称该 RO 在内部轨道变窄时不触发（border-box 不变），
  所以大概率无循环——但**未实测**。
- **未测极端 nmode**：`v-table` 在 nmode=8 时是 16×16 = 256 个 `<td>`（
  `app.js:279` `renderMatrix` 走 `innerHTML` 字符串拼接，本身比 `createElement`
  快，故未列为问题）；gaussian 路径每次 `/run` 重建，未评估大 nmode 下的绝对耗时。
- **未评估后端往返**：`doRun` 的 `setStatus` 里含 `performance.now()` 计时
  （`app.js:489-497`），但那是端到端耗时，本文只审前端渲染段。
- **未验证 `imageSmoothingQuality: "high"` 的实际开销占比**（§2.3 第 5 点）：
  依赖 GPU/驱动，只能实测。

---

*审查日期: 2026-09-17*
*基线提交: `c583d78`*
*方法: 静态审查（无实测 profile）*
*本次未改任何代码*
