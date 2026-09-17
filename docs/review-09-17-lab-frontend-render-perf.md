# Review: Lab 前端渲染性能 / 布局抖动

**审查范围**: `cvsim/lab/static/`（17 个文件：`app.js` 837 行 / `editor.js` 767 行 /
`staff.js` 388 行 / `fock.js` 382 行 / `ops.js` 442 行 / `style.css` 1347 行 / +
`colormap.js` `curve.js` `svg_kit.js` `steps_slider.js` `request.js` `schema_store.js`
`initial.js` `ops_schema.js` `scan_form.js` `default_scene.js` `index.html` `tokens.css`）

**基线**: `c583d78`（2026-09-15）。审查时该状态下 Wigner frame 修复尚为**未提交的
工作区改动**，现已经由 `d997fa4` 落盘；`docs` 提交 `ae3a1dc` 是当前 HEAD。
本文所有 `file:line` 锚点对应**已提交的 `ae3a1dc`（工作区内容与审查时一致）**。
**日期**: 2026-09-17
**方法**: 静态代码审查（读-写交错、强制同步布局、重复计算、DOM 重建范围）+
**实测**（C0 起补 CDP `Performance` 域计数，见 §7；§1 的引用块有摘要）
**未做**: ~~未跑浏览器 profile、未跑 CDP `Performance` 域计数~~ —— **C0 已补 `Performance`
域计数**（`LayoutCount` / `RecalcStyleCount` / `LayoutDuration` / `RecalcStyleDuration`）。
**仍未做** flame chart / CPU profile。原文各条的 `file:line` 证据与可验证断言保留，
定性判断现已用实测数字校准（§1 / §2.1 / §2.2 / §2.4 / §7）。

**本次未改任何代码**（本审查本身；后续 C1–C6 的实施改动见 §0 状态表）。

---

## §0 落地状态总表（2026-09-17 回填）

> ⚠ **本表故意放在文档最前**：文档已超过 Trellis 的
> `context_injection.max_file_bytes`（32768）注入上限，下游任务读到的版本会**按字节
> 截断尾部**。故状态与"与原判断不符的修正"必须前置，不能只写在各节的批注里。
> 每条详细证据仍在对应小节（以引用块附加，原 `file:line` 锚点未删）。
>
> **截断规则（不必记精确边界 —— 它会随本表变大而前移）**：
> 窗口只有前 32768 **字节**，而本表本身在窗口内，故**每次往本表加内容，边界都会往前移**。
> 因此**不要依赖"某节一定在窗口内"**。当前实测（文档 ~62KB，已含 C0 回填）：
> 窗口内 ≈ §0 + §1 + §2（含 §2.1–§2.5）+ §3 前段；**§4 起（byte 44657）全部在窗口外**
> （含 §4 P2 全部 5 条、§5 勿回退表、§6、§7、§8、§9）。
> 复测方法：`.scratch/trunc-where.mjs`（按字节切片并列出窗口内标题）。
> **结论：凡下游任务需要的依据，要么前置到本表，要么写进该任务自己的
> `prd.md` / `implement.md`。**
> 因此 **C6 的实施依据不在本文**，而在它自己的
> `.trellis/tasks/09-17-lab-css-a11y-misc/prd.md`（8.4KB）与 `implement.md`（6.5KB）
> ——那两份独立完整地记录了 §4.1–§4.5 的代码锚点、修法与 AC，不依赖本文注入。
> 同理 C3 依据 `09-17-lab-drag-layout-thrash/`，C5 依据 `09-17-lab-redundant-work-cleanup/`。
> **§7（量化方案）现在已在截断外**，故其**实测数字已前置到 §1 的引用块**
> （三场景 `LayoutCount` 基线→落地后）；复现命令 `node tests/lab_render_perf_probe.mjs`。
> **§9（实施中新发现的 4 个问题）也在截断外**：其中 §9.1（拖参数滑条后 undo 按钮
> 保持 disabled）是**真实缺陷且改动前就存在**，需独立任务处理。
>
> **⚠ §5「已经做对的（勿回退）」原表已落到截断窗口外**。
> 因该表是父任务 AC4 的「勿回退」清单、且 C6/C3 尚未做完，故**要点前置如下**
> （原表连同 `file:line` 锚点仍在本文 §5，未删）：
>
> | 机制 | 为什么不能回退 |
> | --- | --- |
> | seq guard + 引用计数 busy（`request.js` / `app.js`） | 过期请求静默丢弃、busy 计数不串台（曾修控件卡死） |
> | run debounce 120ms（`app.js`） | 参数拖动只在停手后发一次请求——**这层已经对了**，卡顿来自它之外的同步 DOM 工作 |
> | 拖拽期抑制 emit（`editor.js`） | 拖动中不逐帧发请求，drop/取消后单次 |
> | **`onParam` 不调 `staff.render()`** | 有意为之——重建 DOM 会中断 range 拖动（C5 因此没把 `onParam` 改走 `syncChrome()`） |
> | 用引用比较的不可变历史（`editor.js`） | 每步 O(1)，无深拷贝 |
> | `.wigner__side` 用 `max-width` 而非 `minmax` 轨道 | `minmax` 会把轨道钉到 max，内容窄时仍挤压缩 frame；由 `test_wigner_side_column_is_width_capped` 锁定 |
> | 零外部资源 | 本地工作台硬约束 |
> | 无 `backdrop-filter` / 无 `filter` / 无非合成动画 | 无整层重绘源；`transition` 只作用于 `background-color`/`color`/`transform`/`opacity` |
>
> **另有反向约束**（父任务 AC6）：**不得**引入 `contain` / `content-visibility`
> —— 隐藏面板已由 `[hidden] { display: none !important }` +
> `.fold:not([open]) > * { display: none }` 做到零布局成本。
> 该约束已由 `test_wigner_frame_sizing_is_css_only` 反向断言。

| 条目 | 状态 | 一句话结论 |
| --- | --- | --- |
| §2.1 cutoff 滑条全量 render | ✅ 已落地（C1） | 走 `syncChrome()`；**但必须定点补模行标签**——`modeLabel` 内嵌 `initial`，而 `clampInitial` 夹到 `cutoff-1` |
| §2.2 参数滑条强制布局 + 3 select 重建 | ✅ 已落地（C1） | 实测 4 次 input：`rect=8/computedStyle=4/matchMedia=4` → 全 **0** |
| §2.3 热图全量重算 | ✅ 已落地（C2） | 修法 5 处中 1/2/4 已做；**3 只做了 canvas RO**（3 个 fit RO 归 C4）；**5 实测否决** |
| §2.4 `dragover` 读写交错 | ✅ 已落地（C3） | 方案 (a)；实测 rect **2→1**/事件、qsa **1→0**/事件；ghost 几何逐位一致 |
| §2.5 bosonic 分步滑条 | ⚠ 部分（C2） | 离屏缓存已落地；**rAF 节流未做**（见该节批注） |
| §3.1 删除 `fitWignerFrame` | ✅ 已落地（C4） | 方案 A 成功；6 条几何不变量全绿；**gap 无需补偿**、窄屏**不能用 `aspect-ratio`**（见该节批注） |
| §3.2/§3.3/§3.4 离屏 canvas / 尺寸赋值 / 遍历合一 | ✅ 已落地（C2） | 像素门逐字一致 |
| §3.5/§3.6/§3.7 重复劳动 | ✅ 已落地（C5） | R4 只对 `fock.js` 有实际工作（`app.js` 两处本来就只读一次）；R1 陷阱是**不能提到模块顶层**；R2 覆盖 `setInitial`（C1 已改走 `syncChrome`） |
| §3.11 `drawFidSvg` 去 `innerHTML` | ✅ 已落地（C2 R8） | C5 的 R5 应记为「已由 C2 承载」，未重复实现 |
| §3.12 `drawAxes` 节点复用 | ⬜ 未做（C2 R9 显式跳过） | 实测 20 个元素、属性几乎全随 `w`/`h`/`lim` 变 → 收益不足；C5 R6 沿用该结论 |
| §3.8 `renderPalette` 全量重建 | ✅ 已落地（C1） | C5 的 R3 应记为「已由 C1 承载」 |
| §3.9 `setView` 全量 render | ✅ 已落地（C1） | 走 `syncChrome()` |
| §3.10 joint 热图 rect | ✅ 已落地（C2） | WeakMap 按 SVG 分键；双向守卫 |
| §4.1 `*` 滚动条改 `:root` | ❌ **实测否决（C6）** | 前提"两个属性都可继承"**只对一半**：`scrollbar-width` **不**继承 → 5/5 容器滚动条 12px→17px。保留 `*`，加**反向**断言守护 |
| §4.2 `#staff` 的 `aria-live` | ✅ 已落地（C6） | 移除；`#status` 的 `role` + `aria-live` **两者保留**（唯一播报口） |
| §4.3 `scrollIntoView` 进 rAF | ✅ 已落地（C6） | 两处都在 rAF 内；`lab_scan_probe` 守卫 |
| §4.4 `init()` 串行 `await` | ✅ 已落地（C6） | `/health` 不再 await。**行为级 A/B**：CDP 扣住 `/health`，改动前 15s 不 boot，改动后 541ms boot |
| §4.5 不加 `contain`/`content-visibility` | ✅ 已核验（C6） | 零命中；`container-type` 不算 |
| §7 量化验证方案 | ✅ **已执行（C0）** | 新增 `tests/lab_render_perf_probe.mjs`；三场景实测：S1 `LayoutCount` **93→64**、S2 **268→90**、S3 **14→13**；3 次采样计数完全一致 |

> **实测摘要（C0，替代上表原定性判断）**——完整表与复现命令见 §7，
> 三场景均已前置到对应小节（§2.1 / §2.2 / §2.4）：
>
> | 场景 | `LayoutCount` 基线 → 落地后 | 变化 | `RecalcStyleDuration` |
> | --- | ---: | ---: | ---: |
> | S1 cutoff 滑条（100 步 `input`） | 93 → 64 | −31.2% | 0.0340 s → 0.0173 s（−49.2%） |
> | S2 参数滑条（100 步 `input`） | 268 → 90 | **−66.4%** | 0.0647 s → 0.0031 s（**−95.2%**） |
> | S3 `dragover`（20 次） | 14 → 13 | −7.1% | 0.0048 s → 0.0038 s（−22.2%） |
>
> **S2 降幅最大**，印证 §2.2「`onState` 强制布局是最贵的一条」。
> **S3 降幅小不代表性**：浏览器对同帧 `dragover` 会合并布局，
> 故其收益主要体现为**每次事件少 1 次强制布局读**（rect 2→1）与
> **消除全树查询**（qsa 1→0）——核心证据是 §2.4 的探针计数器，不是本表。
> **复现性**：`--runs=3` 的 `LayoutCount` 三次完全一致（64/64/64、90/90/90、13/13/13）；
> 仅 `*Duration` 有毫秒级抖动，报告同时给 `_min`/`_max`，**不取最小值冒充**。
> **诚实边界**：同机同视口相对对拍，非跨机绝对值；"频率 ~60–120/s"仍是事件模型推算；
> 未做 flame chart。

**与原判断不符的三处修正（最重要）**：

1. **§2.2 的"`matchMedia` 有 8 个调用点"是错的** —— 实测全文件 `matchMedia` 计数
   **= 1**（仅 `app.js:53`）。那 8 行是 `fitWignerFrame()` 的**调用点**。修法退化为
   单点提升，且**不需要** `addEventListener("change", ...)`：`MediaQueryList.matches`
   是活属性，缓存对象 ≠ 缓存结果。
2. **§2.2 的"脏键 = `nodes` 引用"永远不可能命中** —— `onParam` 用
   `state.nodes.map(...)`，`map` 恒返回新数组。写成引用比较等于没改（静默空操作）。
   必须用节点身份 `(id, op)`。
3. **§2.3 修法 5（降到 `"medium"`）实测否决** —— 4 个用例像素哈希**全部改变**。
   父任务"改视觉即越界"，故保留 `"high"`。

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

> **实测列（✅ C0，`tests/lab_render_perf_probe.mjs`，3 次采样，基线 `c583d78`
> 的 `static/` vs 落地后）**：上表的"触发频率"是**事件模型推算**，
> 下表是**实测累计代价**（100 步滑条 / 20 次 dragover）。完整表与复现命令见 **§7**。
>
> | 场景 | `LayoutCount` 基线 → 落地后 | `RecalcStyleDuration` |
> | --- | --- | --- |
> | S1 cutoff 滑条（100 步）→ §2.1 | **93 → 64**（−31.2%） | 0.0340 s → 0.0173 s（−49.2%） |
> | S2 参数滑条（100 步）→ §2.2 | **268 → 90**（−66.4%） | 0.0647 s → 0.0031 s（−95.2%） |
> | S3 dragover（20 次）→ §2.4 | **14 → 13**（−7.1%） | 0.0048 s → 0.0038 s（−22.2%） |
>
> S2 降幅最大，印证 §2.2 的判断（`onState` 的强制布局是三条路径里最贵的）。
> S3 的收益主要体现为**每次事件少 1 次强制布局读 + 消除全树查询**，
> 在 `Performance` 计数上不显眼（浏览器对同帧 `dragover` 会合并布局）——
> 其核心证据是 §2.4 的探针计数器（rect **2→1**、qsa **1→0**）。

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

**验证断言**: 连续 100 次 `input`，修复后 `LayoutCount` 增量显著低于基线。

> **✅ 已落地（C1）** —— 本条目由 `09-17-lab-interaction-path-rerender` 承接。
>
> **实测（C0，`tests/lab_render_perf_probe.mjs`，100 步真实 `input`，3 次采样）**：
>
> | 指标 | 基线（`c583d78` 的 `static/`） | 落地后 | 变化 |
> | --- | ---: | ---: | ---: |
> | `LayoutCount` | **93** | **64** | **−31.2%** |
> | `RecalcStyleCount` | 97.7 | 70 | −28.3% |
> | `LayoutDuration` | 0.0460 s | 0.0307 s | −33.2% |
> | `RecalcStyleDuration` | 0.0340 s | 0.0173 s | −49.2% |
>
> 上表「滑条 `input` 在拖动时约 60–120 次/秒」是事件模型推算；
> 上表实测的是**每 100 次 `input` 的累计代价**。完整表与复现命令见 §7。

**修法**（对齐 `setInitial` 先例）: cutoff 变化只影响 `cutoffs`/`initial` 字段，
不改变 staff **树结构**与托盘内容。改为

```js
state = { ...state, ...patch };
renderJson();
hooks.onState(state);
emit(toV1Json(state));
```

即 `setCircuit` 不复用 `render()`；若担心 `renderFockControls` 里的
`syncFockInputValues()`（`editor.js:694-704`）遗漏，单独调它。

> **⚠ 落地时的实测修正（C1）**：上面「不改变 staff 几何」只说对一半。
> `modeLabel`（`staff.js:14-25`）把 `state.initial` 的光子数**渲进模行标签**
> （`mode m · |n⟩`），而 `clampInitial`（`fock.js:85-92`）把 initial 夹到
> `cutoff - 1` —— 故拖 fock cutoff **会改标签**。实测：
> `cutoff 10, initial [5] → "mode 0 · |5⟩"`；`cutoff 3 → initial 夹成 [2] → "mode 0 · |2⟩"`。
> 若照上面这样"整个跳过 staff 更新"，屏幕会停在陈旧的 `|5⟩`。
> 落地实现：不重建 staff 树，但定点补标签（`staff.syncLabels()`，只改
> `.staff__mode-label` 的 `textContent`）。
>
> 另外，`render()` 的副作用实际有 **8** 项（上面列了 6 项，漏了 undo/redo 按钮的
> `disabled`，`editor.js:409-410`）——而 `setInitial`（`editor.js:601-612`）与
> `onParam`（`editor.js:489-495`）各自**手抄了同一串**。落地时抽成单一函数
> `syncChrome()`，使"轻量路径漏掉某个副作用"在结构上不可能发生。

**验证断言**: 拖 cutoff 滑条时 `staff.render()` 与 `renderPalette()` 的调用次数为 0。
（已落地为 `tests/lab_interaction_probe.mjs` 检查 6：用 DOM 节点**身份**而非调用
计数——`replaceChildren()` 会销毁被标记节点，节点存活即证明从未重建。）

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
（`app.js:53`）每次调用都**新建一个 `MediaQueryList` 对象**。该调用在文件内
**只有 1 处**（即 `fitWignerFrame` 内部那一次），但它被 `fitWignerFrame` 的
**8 个调用点**反复触发（`app.js:127/216/221/222/260/265/284/446`，其中 3 个是
`ResizeObserver` 回调）。

> 勘误（C1 落地时实测）：本节初稿把 `app.js:127/216/221/222/260/265/284/446`
> 写成「`matchMedia` 的 8 个调用点」。实测 `git show HEAD:cvsim/lab/static/app.js`
> 全文件 `matchMedia` 计数 = **1**；那 8 行是 `fitWignerFrame()` 的调用点。
> 结论（每次滑条都新建 MQL 对象）不变，但修法退化为**单点提升**，非 8 处替换。

**修法**:
1. `onParam` 路径不做 `refreshScanNodes()`——加脏键（节点身份 + `nmode` 未变则
   早退），或把 `onState` 拆成 `onNodesChanged` / `onBackendChanged` 两个钩子；
   ⚠ 脏键**不能用 `state.nodes` 数组引用**：`onParam` 用 `state.nodes.map(...)`
   重构数组，而 `map` 无论元素是否变化都返回新数组 → 引用比较**永不命中**，
   写成引用比较等于没改（实测）；
2. `syncBackendPanels` 在 backend 未变时整体早退（含末尾的 `fitWignerFrame()`），
   **但首次调用必须放行**（`init()` 也要靠它做首屏面板显隐）；
3. `fitWignerFrame` 里的 `matchMedia` 提升为模块级单例（1 处，非 8 处）。
   **不需要** `addEventListener("change", ...)`：`MediaQueryList.matches` 是
   **活属性**，每次读取都按当前 viewport 求值，故缓存对象不等于缓存结果——
   语义与改动前逐字一致。

**验证断言**: 拖参数滑条时 `getBoundingClientRect` / `getComputedStyle` / `matchMedia`
调用次数为 0。（已落地为 `tests/lab_interaction_probe.mjs` 检查 1；改动前实测
`rect=8 computedStyle=4 matchMedia=4`，改动后全 0。）

> **✅ 已落地（C1）** —— 本条目由 `09-17-lab-interaction-path-rerender` 承接。
>
> **实测（C0，`tests/lab_render_perf_probe.mjs`，100 步真实 `input`，3 次采样）**
> —— 这是三条路径里**降幅最大**的一条，印证了本条"最贵"的判断：
>
> | 指标 | 基线（`c583d78` 的 `static/`） | 落地后 | 变化 |
> | --- | ---: | ---: | ---: |
> | `LayoutCount` | **268** | **90** | **−66.4%** |
> | `RecalcStyleCount` | 179.7 | 90 | −49.9% |
> | `LayoutDuration` | 0.0754 s | 0.0187 s | −75.2% |
> | `RecalcStyleDuration` | 0.0647 s | 0.0031 s | **−95.2%** |
>
> `RecalcStyleDuration` 几乎归零（0.0647 s → 0.0031 s），因为 `fitWignerFrame`
> 的强制样式重算已被结构性删除（§3.6 / C4）。完整表与复现命令见 §7。

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

> **✅ 落地结果（C2 / `09-17-lab-heatmap-redraw-cache`），逐条实测**：
> 1. ✅ 已落地。缓存键 = **(W 引用, n)** —— 必须含 n，否则漏掉 dpr 变化
>    （实测 dpr 1→2 时目标位图 303² → 606²，源位图仍是 64²）。缓存的是 n×n 源位图，
>    不是目标位图（目标尺寸随容器变）。
> 2. ✅ 已落地（`if (canvas.width !== pw)` 守卫）。附带说明：同值赋值的危害不止性能
>    —— 它会清空位图，任何依赖该副作用的代码都会在加守卫后暴露。本项目
>    `clearRect` + `drawImage` 覆盖整块画布，故无影响（像素门逐字一致即证据）。
> 3. ⚠ **部分落地**：只有 **canvas 的 RO** 按本项合并到一帧一次
>    （`wignerRafPending` 去重）。`wignerBox` / colorbar / side 那 3 个 fit RO **未动**
>    —— 按 parent 消解规则它们归 C4（`09-17-lab-remove-fitwignerframe`）整体删除，
>    此处合并会白做。
> 4. ✅ 已落地为 `colormap.js` 的新导出 `inspectWignerGrid(W)`；抛错语义与原
>    `validateWignerGrid` 逐字一致（测试逐条对拍），旧导出保留未删（探针仍在用）。
> 5. ❌ **实测否决**：改 `"medium"` 后 4 个用例（2 场景 × 2 dpr）的 toDataURL 哈希
>    **全部改变**（displace@dpr1 `409c7ca0` → `95390307` 等），可见差异成立。
>    父任务 Out of Scope 明令"改视觉即越界"，故**保留 `"high"`**，并加
>    `test_r6_kept_high_smoothing` 守卫。注：原文估"n=64 → 1024 是 16×"，
>    实测是 4.7×（dpr1）/ 9.5×（dpr2），量级不同但结论一致。
>
> **像素门**：`tests/lab_heatmap_pixel_probe.mjs` + 改动前录制的
> `tests/lab_heatmap_pixels.json`。基线**先于改动**取得，故"逐字一致"不是事后自证。
> 附带发现：colorbar 哈希在 4 个用例里完全相同（`3cf6bb7098af2bf4`）——直接证明
> 色带与 W / 尺寸 / dpr 全无关，故 R4 只需画一次（但 `drawWignerResult` 的 singular
> 分支会 `clearRect`，那里必须复位标志，否则色带永久留白）。

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

> **✅ 已落地（C3 R1–R4，2026-09-17）**：修法 1–4 **全部落地**，
> 几何缓存采用**方案 (a)**（缓存 grid 相对 root 内容区偏移）。
> **探针计数器实测**（10 次 dragover，走托盘卡片真实 `dragstart`）：
>
> | 指标 | 改动前 | 改动后 |
> | --- | --- | --- |
> | `getBoundingClientRect` / 事件 | **2.0** | **1.0** |
> | `querySelectorAll` / 事件 | **1.0** | **0.0** |
>
> **修法 1 的"失效点"实测不存在**：缓存值 = `gridRect.left - rootRect.left
> + root.scrollLeft`，公式里每次都重新减去当前 `scrollLeft`，
> 故与滚动位置无关 —— 实测 `scrollLeft=40` 时重算 delta 仍为 **0**。
> window resize 也不改变该**内部**偏移。故 `dragstart` 之后无需任何失效逻辑。
>
> **修法 4 的几何未变**：ghost 改 `transform` + `left/top` 归零后，
> rect 相对 grid 仍是 `relLeft 210` / `relTop 6` / 60×32 —— **逐位一致**，
> `.gate { margin-top: 6px }` 的偏移关系未被破坏（`transform` 是绘制后位移）。
> 未加 `will-change`（父任务 Out of Scope：不引入额外层）。
>
> **本节锚点已过期**：`staff.js:189/194/214-216/228-229` 是改动前行号；
> 另 `clearHover()` 内**还有第二处**同款 `querySelectorAll`（`staff.js:71`），
> 本节未提及 —— 两处都已改为 `prevLane` 引用。
>
> 守卫：4 条源码级断言（`test_dragover_reads_layout_at_most_once_and_never_queries_all`
> 等，均验证过改动前为红）；行为守卫 `lab_staff_probe.mjs` **40/40 PASS**。
> 一处连带修正：该探针原先用 `ghost.style.left` 判位置（R4 后恒为 `0px`），
> 已改为读**实测几何**并新增一条 R4 断言 —— 属表示耦合，非行为回归
> （同次运行放置列号 `placedX` 仍为 8）。

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

> **⚠ 部分落地（C2）**：离屏缓存已落地（§2.3），故滑块快速拖动时热图重算的成本
> 已大幅下降。但 **rAF 节流未做** —— 节流的正确性要求"末次事件不能被丢弃，
> 停手后显示的 step 必须与滑条值一致"，而 `show(k)` 除画布外还写 tag / info /
> meters 三处文案；把整条 `show()` 塞进 rAF 会引入"文案滞后于滑条"的新问题，
> 需要把"文案写入"与"重绘"拆开才能安全节流。该拆分超出 C2 范围（本任务聚焦
> 重绘成本），故显式留待后续任务。
> **当前状态：`slider.oninput = () => show(slider.value)` 仍逐事件执行**，
> 收益只来自缓存命中（不再重复 `createImageData` 与逐格 LUT 映射）。
> `lab_bosonic_probe.mjs` 的"slider to step 0 updates tag"仍 PASS，即文案同步未受影响。

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

> **✅ 已落地（C4 / `09-17-lab-remove-fitwignerframe`），方案 A 成功**：
> 在 `1fr` 轨道上加查询容器 `.wigner__fit`（`container-type` 窄屏 `inline-size` /
> 宽屏 `size` + `align-self: stretch`），frame 用 `max(64px, 100cqw)` /
> `max(64px, min(100cqw, 100cqh))`。**未采用固定 colorbar 列的退路**——`auto` 列保留，
> 故不变量 3 原样有效，6 条几何不变量全绿且**未放宽任何断言**。
>
> **原文两处判断被实测修正**：
> 1. **gap 归属**：`availW` 与 `1fr` 轨道宽**逐位相等**（1440：`334.72 − 12 = 322.72`
>    = 轨道宽 = frame 宽；`frame.left == box.left`；`.wigner` 无 padding/border），
>    故**不需要** `calc(100cqw - gap)` 补偿。
> 2. **窄屏不能用 `aspect-ratio`**：原文建议 `<80rem` 用 `width: 100%; aspect-ratio: 1`。
>    落地改用 `container-type: inline-size` + `height: max(64px, 100cqw)`。原因：
>    `aspect-ratio` 遇双 definite 尺寸会失效（原实现绕开它的理由），且窄屏需要
>    64px 下限参与方形计算——`aspect-ratio` 与 `max()` 组合会产出非正方形。
>
> **落地时探针抓到的真实缺陷（目测不可辨）**：首轮只写
> `max(64px, min(100cqw, 100cqh))`，探针报 fock@1280 `frame=57.25 expect=64 (err -6.75)`。
> 根因：frame 从 grid item 变成 **flex item**，默认 `flex-shrink: 1` 在列宽 < 64px 时
> 把它压回 57.25，**使 64px 钳位失效**。修法 `flex: none`。该 6.75px 恰好压进 12px gap。
>
> **几何对拍**：5 视口 × 19 字段 diff，**4/5 逐位相同**；1920 差 **0.19px**
> ——旧 JS 用整数 `clientHeight`(513)，CSS 解析真实 512.81，**改后更准**。
>
> **顺带退役**：C1 的 `test_wigner_breakpoint_query_is_a_singleton`——`WIDE_QUERY` 是
> `fitWignerFrame` 的唯一消费者，函数删除后它失去对象（断点判断改由 CSS `@media`
> 承担，JS 侧再无 `matchMedia`）。这不是回退 C1 R5：其目的以更强方式消失。
>
> **已知边界**：窄屏（`<80rem`）**无自动探针覆盖**（所有浏览器探针都用 ≥1100 视口）；
> 本任务手工对拍了 1100/900 但未纳入 CI 门。

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
| ~~`app.js:48`（`fitWignerFrame`）~~ | ~~1/次调用~~ | **已消失（C4）**：整个函数被删除，这行 `getComputedStyle` 随之不存在 |
| `app.js:618`（`drawScanCurve`） | 1/次 | 取 `--color-rule` `--color-ink` `--color-accent`（`619-621`） |
| `fock.js:118-120`（`cssVar`） | — | `drawBars` 调 **4 次**（`fock.js:126-129`），`drawJointPair` 调 **2 次**（`195-196`） |

每次 `getComputedStyle` 都是一次样式解析入口；`fock.js` 的 `cssVar` 每次调用都
重新取 `document.documentElement` 的 computed style。

**修法**: 抽一个 `readThemeVars([...names])` 单点，一次 `getComputedStyle` 读全部；
或在 `MatchMedia("(prefers-color-scheme)")` / 主题变更时缓存失效。项目已有
`--color-*` 主题层（`tokens.css`），缓存是安全的。

> **✅ 已落地（C5 R4，2026-09-17）**：`fock.js` 的 `cssVar()` 已换成
> `readThemeVars(names)`（单次 `getComputedStyle`），`drawBars` 4 次 + `drawJointPair`
> 2 次 → 各 1 次。回退色原样保留。
> **与原表两处不符（实测）**：
> 1. `app.js:177`（`drawAxes`）与 `app.js:618`（`drawScanCurve`）**各自本来就只有
>    一次** `getComputedStyle`（先取 `style` 对象，再对它多次 `getPropertyValue`）
>    —— 本来就没有可合并的重复，C5 未改这两处。
> 2. 表里 `~~app.js:48~~` 那行随 C4 删除整个 `fitWignerFrame` 而消失。
>
> **注**：`readThemeVars` **不跨调用缓存**（每次绘制重新读一次 computed style），
> 故不存在主题切换失效问题。唯一的陷阱是**别把它提到模块顶层**——已加断言守卫。
> 守卫：`test_fock_theme_vars_read_in_one_pass`（验证过改动前为红）。

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

> **✅ 已落地（C5 R1，2026-09-17）**：`const R = renames();` 已提到
> `for (const n of state.nodes)` 之外。
> **唯一陷阱（规划未提）**：**不能**提到模块顶层 —— schema 注入发生在
> **import 之后**（`schema_store.js` 的 `setSchemaTables` 在启动期 `/schema` 到达时
> 调用），顶层取值会拿到**注入前的回退常量**（`UI_TO_V1_OP` 等），
> 于是 schema 驱动的改名全部失效。已加断言守卫这一条。
> 守卫：`test_renames_hoisted_out_of_node_loop`（验证过改动前为红）。

### §3.7 【P1-12】单次 mutation 序列里 `toV1Json` 被调两次

**位置**: `editor.js:399`（`renderJson`）与 `editor.js:411`（`emit`）——`render()` 内；
另外 `editor.js:484-486`（`onParam`）与 `editor.js:601-603`（`setInitial`）也是
`renderJson()` + `emit()` 各算一次。

`toV1Json` 是 O(节点数) 的对象构造 + 字符串化。修法：算一次，两处共用。

> **✅ 已落地（C5 R2，2026-09-17）**：`renderJson(doc)` 改为接收**已算好的** doc
> （参数变必填），`syncChrome()` 与 `onParam()` 各自只算一次并共用同一对象。
> "算两遍"现在**结构上不可能**（无默认参数可退）。
> **形态差异保持**：`renderJson` 仍 `JSON.stringify(doc, null, 2)`（2 空格缩进字符串
> 给 `#json-input`）；`emit(doc)` 传的仍是**对象**本身（`hooks.onRun` 契约）。
>
> **修正本节的锚点**：`setInitial` **不在**未修之列 —— C1 已把它改走 `syncChrome()`
> （`editor.js:632-633` 的 `if (!staff.syncLabels()) render(); else syncChrome();`），
> 故 R2 的改动自动覆盖它。本节原文 `editor.js:601-603` 是 C1 之前的行号。
> 同理 `editor.js:484-486`（`onParam`）的 `renderJson()` 是**不带参数**的旧形态。
>
> **字节冻结（AC2）**：改动前经真实导入路径落盘 4 个 payload 的基线，
> 改后 **4/4 逐字节相同**。长期守卫是既有 golden
> `test_default_scene_to_v1_byte_frozen`；本次新增
> `test_one_to_v1_json_per_mutation`（验证过改动前为红）。
>
> **诚实边界**：实测 `Performance.getMetrics` 60 次合成 input 为
> `ScriptDuration 0.0083s`（≈0.14ms/次）——量级太小、噪声主导，
> **不足以证明收益**；该数字不是 A/B 对比。R2 的确定性收益（少一次全节点遍历）
> 由源码断言守卫，真正的量化属 C0 任务。

### §3.8 【P1-13】`renderPalette()` 每次 `render()` 全量重建

**位置**: `editor.js:405` 调用；`editor.js:505-556` 实现。托盘内容**只依赖
`state.backend`**（`opsForBackend(state.backend)`，`editor.js:508`）。

项目里已有正确的缓存范式：`editor.js:656-660` 用
`dom.initialInputs.dataset.nmode`（`initialCacheKey`）早退。照抄即可：

```js
if (dom.palette.dataset.backend === state.backend) return;
dom.palette.dataset.backend = state.backend;
```

> **✅ 已落地（C1 / `09-17-lab-interaction-path-rerender` R6）**，与上面写法逐字一致。
> 落定时核过：托盘是**无状态纯列表**（无输入框、无焦点值），故早退无需补写副作用
> ——即与 `initialInputs` 先例不同，这里不需要"早退前先补一次"的那一步。

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

> **✅ 已落地（C1 R4）**，改走 `syncChrome()`（即 `renderJson` + `renderFockControls`
> + `onState` + undo/redo 按钮态 + `emit`）。注意 `renderFockControls()` **必须**保留
> 在这条路径上：它同步 joint-modes 选择与 fock 数字输入，故 `joint_modes` 的改动
> （`app.js:706` `setJointModes` → `setView`）靠它落地。探针检查 5/6 锁定
> staff + palette 不再重建。

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

> **✅ 已落地（C2 R7）**：rect 复用改为 **WeakMap 按 SVG 分键**
> （`jointSvg` / `batchSvg` 各一份缓存），键含 `rows` / `cols` / `color`。
> 形状或颜色变 → 重建（rect 的 x/y 按格坐标写死，复用会错位）；仅透明度变 →
> 只改 `fill-opacity`，且**值未变则跳过写入**。上限 900 格来自后端
> `schema.py:139` 的 cutoff 上界 30，非前端常量。
> **双向守卫**：`tests/lab_heatmap_rect_probe.mjs` 同时验证"必须复用"与
> **"形状变化必须失效"**——永不失效的缓存比没有缓存更糟。
> 实测：cutoff 10 → 100 rect（`viewBox="0 0 10 10"`），cutoff 25 → 重建为 625 rect
> （`viewBox="0 0 25 25"`，旧节点未存活），同形状重渲染 → 节点保留。
> `drawBars` 未动（规模小，且柱数上限 30 由 `histBars` 自身控制）。

### §3.11 【P1-16】`drawFidSvg` 用 `svg.innerHTML`

**位置**: `app.js:392-396`。在 SVG 命名空间元素上写 `innerHTML` 会走 HTML 解析器
路径（外来内容），比 `replaceChildren` + `el()` 慢，且与项目其余 SVG 绘制风格
（`svg_kit.el`）不一致。

> **✅ 已落地（C2 R8）**：改 `replaceChildren` + `el()`，文本用 `textContent`
> （中文标签不再经 HTML 解析）。class 名与元素顺序保持逐字一致，`style.css` 的
> `.bosonic__grid-line` / `.bosonic__line` / `.bosonic__label` 依赖它们；
> `lab_bosonic_probe.mjs` 的 fidelity 曲线断言仍 PASS。

### §3.12 【P1-17】`drawAxes` 每次全量重建 ~15 个元素

**位置**: `app.js:169-208`：`svg.replaceChildren()`（`175`）+ 2 条主线 + 5 条刻度线
+ 8 个 `<text>` ≈ 15 个元素，每个经 `el()` 逐属性 `setAttribute`。
低优先（每次 resize/热图重绘才走），但可复用节点只改属性。

> **⏭ 显式跳过（C2 R9），理由已记录**：实测元素数 = **20**（浏览器实测
> `#axis-svg` 子节点：12 个 `<line>` + 8 个 `<text>`，见下方勘误；原文估"~15"，
> 量级正确）。跳过因为：
> (1) 属性**几乎全部随 `w`/`h`/`lim` 变**——中线坐标依赖 `w`/`h`，刻度位置依赖
> `w`/`h`，文字内容依赖 `lim`，没有"值未变可跳过"的部分；
> (2) R5 已把 canvas RO 合并到一帧一次，resize 风暴下不再重复；
> (3) 规模远小于同任务已处理的 joint 热图（900 rect × 6 attr）；
> (4) 替代方案（单个 `<path>` 画刻度线，20 → ~8 元素）**会改动 DOM 结构**，
> 而 `lab_wigner_layout_probe.mjs` 的命中测试与 `axis-svg` 层叠关系依赖当前结构。
> 故不做；若将来确需，应作为独立任务并重跑几何探针。
>
> 勘误：落地过程中一度写成"~24 个元素（5×2 刻度线 + 4×2 文字）",实测为
> 20 —— 刻度线是 5 条 x + 5 条 y = **10 条**（中线另计 2 条 = 12），文字是
> 4 个 x + 4 个 y = **8 个**（原点无标签）。

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

> **❌ 已实测否决（C6 R1，2026-09-17）—— 本条的判断前提是错的。**
> 上面这句「这两个属性**都是**可继承属性」**只对一半**。实测 Edge 153：
> **`scrollbar-color` 可继承，`scrollbar-width` 不可继承** ——
> `:root { scrollbar-width: thin }` 只让 `<html>` 算得 `thin`，
> `<body>` 与全部后代回落 `auto`：
>
> ```
> html → thin      body → auto      div → auto
> div 的 scrollbar-color → oklch(...)  ← 这个继承了
> ```
>
> **后果（同构 A/B + 真实页面 5 容器对拍）**：滚动条槽宽 **12px → 17px**，
> 5/5 容器的 computed `scrollbar-width` 全变、4/5 的实际槽宽变宽。
> 违反「改视觉即越界」，故**保留 `*`**。
>
> **这不是"待优化"，而是"不可优化"**：既然该属性不继承，除 `*`（或逐个列容器
> 选择器，会漏掉将来新增的容器）外，没有写法能让每个滚动容器都拿到 `thin`。
> 代价（`*` 命中整棵树）**必须接受**。
>
> 守卫方向已翻转：`test_scrollbar_rule_stays_universal_not_root` 断言 `*` 版
> **必须存在**、`:root` 版**不得被重新引入**（与 §3.1 的 `container-type`
> 反向断言同型）。
> 证据：`.scratch/c6-ab.mjs`、`.scratch/c6-gutter-{before,after}.json`、
> `.scratch/c6-sw-support.mjs`。

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

> **✅ 已落地（C6 R2）**：`#staff` 去掉 `aria-live="polite"`，保留 `class="staff"`
> 与 `aria-label="五线谱电路编辑区"`。`#status`（实测在 `index.html:224`，
> 非本节的 `:219`）的 `role="status"` + `aria-live="polite"` **两者都保留**
> —— 断言同时锁两个方向，防误删唯一播报口。
> 守卫：`test_staff_is_not_a_live_region`（验证过改动前为红）。

### §4.3 【P2-20】`scrollIntoView` 紧跟 DOM 写入 → 强制 layout flush

**位置**: `app.js:479`（`showMeasurement`）、`app.js:676`（`doScan` 成功回调）。

```js
measurementPanel.hidden = false;
measurementPanel.scrollIntoView({ block: "nearest" });   // 立即读布局
```

各一次/操作，频率低，但属同一类抖动。可放进 rAF。

> **✅ 已落地（C6 R3）**：两处都包进 `requestAnimationFrame`。
> **锚点更正**：实测两处在 `app.js:503`（`showMeasurement`）与 `app.js:720`
> （`doScan` 的 `onOk`），非本节的 `:479` / `:676`。
> 守卫：`test_scroll_into_view_runs_in_animation_frame`（断言恰好 2 处、
> **都**在 rAF 内、无裸调用残留；验证过改动前为红）；
> 行为守卫 `lab_scan_probe.mjs` + `lab_wigner_layout_probe.mjs` 全绿。

### §4.4 【P2-21】`init()` 串行 `await`

**位置**: `app.js:795`（`fetch("/schema")`）与 `app.js:816`（`fetch("/health")`）。

`/health` 只用来填版本号（`app.js:817`），**不参与 `schemaOk` 门控**。串行使首个
`editor.render()`（`app.js:821`）多等一个 RTT。改 `Promise.all` 或让 `/health`
后置不阻塞。

> **✅ 已落地（C6 R4）**：采用"后置"方案 —— `/health` 改为
> `void fetch(...).then(...)`，**不 await**；`/schema` 仍是唯一门控。
> **行为级 A/B 验证**（不只是 grep）：用 CDP `Fetch` 域把 `/health`
> **扣住不放行**，轮询页面是否已 boot：
>
> | | 结果 |
> | --- | --- |
> | 改动前 | `did NOT boot while /health held (within 15s)` |
> | 改动后 | `BOOTED after 541ms with /health HELD`（调色板 3 组、run 按钮可用），页眉版本号在**放行后**才从 `"cvsim —"` 填成 `"cvsim 0.1.0 · circuit_v1"` |
>
> 这同时证明了两件事：`/health` **不再挡门**，且它**仍在跑**（版本号照填）。
> 门控行为逐项未变（红条文案、6 个按钮 id、`schemaOk = true` 均由断言覆盖）。
> 守卫：`test_health_does_not_gate_editor_boot`（验证过改动前为红）。
> **诚实边界**：本地 `127.0.0.1` 上**不声称耗时改进**，收益表述为
> "被扣住也能 boot"。

### §4.5 【P2-22】不要加 `contain` / `content-visibility`

隐藏面板已经零布局成本：`[hidden] { display: none !important }`（`style.css:20-22`）
+ `.fold:not([open]) > * { display: none }`（`style.css:82-84`）。这条是**反向记录**：
避免后续优化时误加 `contain` / `content-visibility` 引入新的容器/滚动副作用。

> **✅ 已核验（C6 AC5）**：`grep -rn "content-visibility" cvsim/lab/static/` 与
> `grep -rn "\bcontain:" cvsim/lab/static/` **均零命中**。
> `container-type`（C4 引入的查询容器）**不算命中**。
> 该约束另由 `test_wigner_frame_sizing_is_css_only` 的反向断言承载 ——
> 这比文字 spec 更难绕过，故 C6 **未**把它落 `.trellis/spec/`（判断理由见
> `.trellis/tasks/09-17-lab-css-a11y-misc/research/measurements.md` §6）。

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

## §7 量化验证方案（**✅ 已执行** —— C0，2026-09-17）

`tests/lab_wigner_layout_probe.mjs:40-80` 已有可直接复用的零依赖骨架：
Node ≥22 原生 `fetch` + `WebSocket`、headless Edge（
`C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe`）、CDP `send()` /
`evalJs()`。已按此骨架新增 **`tests/lab_render_perf_probe.mjs`**：

1. `Performance.enable` + `Performance.getMetrics`，读 `LayoutCount` /
   `RecalcStyleCount` / `LayoutDuration` / `RecalcStyleDuration`；
2. 用 `Input.dispatchMouseEvent` 或直接 `evalJs` 派发合成 `input` 事件序列
   （cutoff 滑条 100 步 / 参数 range 100 步 / 20 次 `dragover`）；
3. 断言：修复后 `LayoutCount` 增量显著低于基线（建议先跑基线，把**实测值**写回本文，
   替换 §1 的定性判断）。

### 复现命令

```bash
node tests/lab_render_perf_probe.mjs                          # 采集，打印 JSON，退出码 0
node tests/lab_render_perf_probe.mjs --runs=3 --out=f.json    # 多次采样（报 min/max）
node tests/lab_render_perf_probe.mjs --compare=baseline.json  # 与基线对拍
```

### 环境验证（C0.1，动手前先做）

原计划的**最大不确定项**是 `Input.dispatchMouseEvent` 能否驱动 HTML5 DnD。
**实测结论：可以**（`.scratch/c0-env-verify.mjs` 环境验证）：

| 问题 | 实测 | 结论 |
| --- | --- | --- |
| 鼠标 press+move 能否触发 `dragstart`/`dragenter`/`dragover` | `dragstart 1`、`dragenter 7`、`dragover 2`，且**真的放下了一个门**（`ops.length` 3→放置成功） | ✅ 真实管线可用 |
| `Input.dispatchDragEvent` 专用 API | `dragenter` +2（`dragover` +0） | ✅ 可用，但鼠标路径已足够 |
| 真实输入能否驱动 range 滑条 `input` | `input` +6、`change` +1、value 1→1.7 | ✅ 可用 |

故 **S1/S2/S3 全部走真实输入管线**（`isTrusted === true`），**无需**退到
`evalJs` 合成事件 —— 报告里的数字是真实管线代价，不是"事件处理代价"。

### 实测基线 vs 落地后（同机、同视口 1440×900、各 3 次采样）

**基线**：`HEAD = 6ab2fe7` 但 `cvsim/lab/static/` 检出 `c583d78` 的版本
（`staticDirty: true`，8 个文件）。**落地后**：`HEAD = 6ab2fe7` 全绿、
`staticDirty: false`。探针会记录 `staticDirty` 字段，避免把数字归错 revision。

| 场景 | 指标 | 基线 | 落地后 | 变化 |
| --- | --- | ---: | ---: | ---: |
| S1 cutoff 滑条（100 步） | `LayoutCount` | **93** | **64** | **−31.2%** |
| | `RecalcStyleCount` | 97.7 | 70 | −28.3% |
| | `LayoutDuration` | 0.0460 s | 0.0307 s | −33.2% |
| | `RecalcStyleDuration` | 0.0340 s | 0.0173 s | −49.2% |
| S2 参数滑条（100 步） | `LayoutCount` | **268** | **90** | **−66.4%** |
| | `RecalcStyleCount` | 179.7 | 90 | −49.9% |
| | `LayoutDuration` | 0.0754 s | 0.0187 s | −75.2% |
| | `RecalcStyleDuration` | 0.0647 s | 0.0031 s | −95.2% |
| S3 dragover（20 次） | `LayoutCount` | **14** | **13** | **−7.1%** |
| | `RecalcStyleCount` | 31.0 | 26 | −16.1% |
| | `LayoutDuration` | 0.0035 s | 0.0031 s | −10.2% |
| | `RecalcStyleDuration` | 0.0048 s | 0.0038 s | −22.2% |

**可复现性（AC2）**：`--runs=3` 三次采样的 `LayoutCount` **完全一致**
（S1 64/64/64、S2 90/90/90、S3 13/13/13）；`RecalcStyleCount` 亦一致。
只有 `*Duration` 有毫秒级抖动（如 S1 `LayoutDuration` 0.0279–0.0297 s），
故报告里对多次采样同时给出 `_min` / `_max`，**不取最小值冒充**。

**S3 为何只降 7%**：`dragover` 的 `LayoutCount` 本来就低（14 次事件只 14 次布局，
约 0.7 次/事件）—— 因为浏览器对同一帧内的多次 `dragover` 会合并布局。
C3 的实际收益是**每次事件少 1 次强制布局读**（`getBoundingClientRect` 2→1）
与**消除全树查询**（1→0），这些在 `Performance` 计数上不如 S2 显眼。
S3 的核心证据是探针计数器（见 §2.4），不是这张表。

**S2 为何降幅最大**（−66% 布局 / −95% 样式重算）：确认了 §2.2 的判断 ——
参数滑条每次都经 `onState` 触发 `refreshScanNodes` + `fitWignerFrame` 强制布局。
这是三条路径里最贵的一条，也是本次收益最大的修复。

**诚实边界**：
- "频率 ~60–120/s"仍是事件模型推算（本次测的是**每 N 次事件的累计代价**，
  不是事件速率本身）；
- 这是**同机同视口**的相对对拍，不是跨机绝对性能；
- S3 的收益主要体现为强制布局次数（§2.4 探针计数器），本表不足以体现；
- 未做 flame chart / CPU profile（父任务 Out of Scope）。

---

## §8 未覆盖 / 未验证

- **未做浏览器 profile（flame chart / CPU profile）**：无 flame chart、无 React-DevTools
  类渲染耗时归因。~~无 `Performance` 域计数~~ —— **✅ C0 已补上 `Performance` 域计数**
  （`LayoutCount` / `RecalcStyleCount` / `LayoutDuration` / `RecalcStyleDuration`，
  见 §7）。**仍未做** flame chart 与 CPU profile：§7 的计数能回答"多少次布局"，
  不能回答"时间花在哪一行"。原始代价排序基于 DOM 操作数 × 事件频率的推理，
  现已用 §7 的实测数字校准（S2 降幅最大，与推理一致）。
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

## §9 实施期间发现的新问题（不在原 22 条内）

> 这些是**落地 C1–C6 过程中实测发现**的，原文 22 条审查未涵盖。
> 按父任务"不把非本任务问题捆进来"的约束，均**未在本批次修复**，单列于此。

### §9.1 【缺陷】拖参数滑条改状态，但 `undo` 按钮保持 disabled

**位置**: `editor.js` 的 `onParam`（`renderJson / onState / emit` 三个副作用）。

`onParam` 调 `pushHistory()`（历史栈**确实**入栈了），但**从不写**
`undoBtn.disabled` —— 该写入只在 `syncChrome()` 里（`editor.js:419-420`）。
若按钮初始为 disabled，则**整个会话里它都不会变可用**。

**实测**（headless Edge，`.scratch/undo-param-check.mjs`）：

```
initial undo disabled: true
drag: 1 -> -5 (changed=true)
undo disabled: true -> true        ← 状态变了，按钮没更新
json length: 472 -> 473            ← 确实改了状态
undo click: button disabled, cannot click
```

**影响**：用户拖完参数滑条后无法用按钮撤销（Ctrl+Z 仍可用，
因为 `undo()` 直接调 `render()`，不依赖按钮态）。

**这是改动前就有的缺陷**：`git show HEAD:...editor.js` 与 C1 之前的版本
（`cb08669^`）的 `onParam` 都没有 disabled 写入。**非本批次引入**。

**为何未修**：修它属于"轻量路径漏写一个副作用"——正是 C1 的 `syncChrome()`
要结构性地消灭的那一类。但 `onParam` 有意不走 `syncChrome()`（C1 明确保留：
它会重建 fock 控件，拖动期间重建 DOM 会中断 range 拖动）。故正确修法是
**在 `onParam` 内补两行 disabled 写入**，并评估"拖动期间每步都写"
（60–120 次/秒的属性写）是否可接受 —— 需要单独判断与测试，
不宜捆进 C5（C5 范围是"同一状态算两遍"）。建议独立任务。

### §9.2 【基础设施】浏览器探针的持久 profile 会让改动**假红或假绿**

7 个浏览器探针中，`lab_staff_probe.mjs` 与 `lab_undo_probe.mjs` 原先没清
HTTP 缓存，而它们用**持久** `--user-data-dir`。给 `colormap.js` 新增导出后，
它们取到旧模块 → boot 抛 `SyntaxError: ... does not provide an export named
'inspectWignerGrid'` → 调色板不渲染 → `CDP timeout: Runtime.evaluate`。

**假绿更危险**：若改的是**行为**而非导出签名，旧代码会被静默测过。
已在 C2 修复（两者补 `Network.clearBrowserCache` + `Page.reload`），
7 个探针现全部清缓存。

### §9.3 【稳定性】探针紧邻启动会在 `waitHttp(/health)` 超时

`lab_undo_probe.mjs` 紧随前一探针运行时，曾在 `waitHttp` 超时（exit 1），
紧接重跑即 11/11 PASS。原因是端口/CPU 争用（uvicorn 未就绪），**非代码回归**。
`waitHttp` 的 60s 超时在负载高时可能不足；建议探针间留间隔或加就绪重试。

### §9.4 【缺口】窄屏（`<80rem`）几何无自动守卫

所有浏览器探针都用 ≥1100 视口，故 `<80rem` 的单列分支**没有任何探针覆盖**。
C4 改动该分支（`container-type: inline-size` + `max(64px, 100cqw)`）时，
只能手工对拍 1100/900 两档（结果与改前逐位相同），**未纳入 CI 门**。
建议补一条窄屏几何断言。

---

*审查日期: 2026-09-17*
*基线提交: `c583d78`*
*方法: 静态审查（无实测 profile）*
*本次未改任何代码*
*落地批次: C1 `cb08669`–`0b0146e` / C2 `9a05fc2`–`6d547bc` +
`371a9e1` / C4 `5eeddb5` + `8e7eeab`*
