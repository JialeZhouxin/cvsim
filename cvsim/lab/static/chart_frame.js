/* Gaussian Lab — 图表框架 leaf（review §3.3 #4，ADR-0009）。
   本 leaf 收的是各绘制点重复的**纯几何与主题取值**：

     * `themeVars` + 四张主题色规格表 —— 真正的重复点。原先三处各写
       `getComputedStyle(...)`：app.js 的 drawScanCurve、app.js 的 drawAxes、
       fock.js 的 drawBars/drawJointPair（后者还自带一份同名的局部
       `readThemeVars`）。回退值此前散落且互不一致（`--color-accent` 在
       scan 路径无回退、在 fock 路径回退 `#2e63d1`），现按各自原样收进规格表。
     * `gridSegments` / `axisLabelSpecs` —— drawScanCurve 内联的网格与轴标签。
       当前只有它一个消费者：抽出来是为了能直测（原先埋在 DOM 绘制里，
       node --test 结构上够不到），不是为了复用。

   注意 `drawFidSvg` **不在**此列：它用 CSS class（.bosonic__line 等）着色，
   JS 侧根本不读主题变量，故与 grid/axis 无共享面。

   零 import、零 DOM：元素仍由调用方经 svg_kit.el 建，`style` 由调用方注入
   —— 故本 leaf 可直测（tests/chart_frame.test.mjs）。 */
"use strict";

/** 主题色查找：规格表 key → 值，缺省回退。**style 由调用方注入**
    （调用点传 getComputedStyle(document.documentElement)）—— 故本函数零 DOM。

    回退值语义：空串 = 无回退（原实现如此），调用方拿到空串即写入无效描边色。 */
export function themeVars(style, spec) {
  const out = {};
  for (const [key, [cssVar, fallback]] of Object.entries(spec)) {
    const v = style.getPropertyValue(cssVar).trim();
    out[key] = v || fallback;
  }
  return out;
}

/** n+1 条竖线/横线，等分绘图区（pad 内）；返回**按原绘制顺序交错**的
    {x1,y1,x2,y2} 段列表（先竖后横，逐 i 交替）—— 元素顺序可被探针观察，
    故不做"先全部竖线再全部横线"的重排。 */
export function gridSegments(W, H, pad, n) {
  const segs = [];
  for (let i = 0; i <= n; i++) {
    const gx = pad.l + (i / n) * (W - pad.l - pad.r);
    const gy = pad.t + (i / n) * (H - pad.t - pad.b);
    segs.push({ x1: gx, y1: pad.t, x2: gx, y2: H - pad.b });
    segs.push({ x1: pad.l, y1: gy, x2: W - pad.r, y2: gy });
  }
  return segs;
}

/** 竖线/横线的像素坐标数组（几何用；绘制顺序见 gridSegments）。 */
export function gridLines(W, H, pad, n) {
  const xs = [];
  const ys = [];
  for (let i = 0; i <= n; i++) {
    xs.push(pad.l + (i / n) * (W - pad.l - pad.r));
    ys.push(pad.t + (i / n) * (H - pad.t - pad.b));
  }
  return { xs, ys };
}

/** drawBars 的 y 比例尺：值 v → 基线以上高度（vmax 归一）。
    vmax<=0 → 全 0（防除零；调用方已用 Math.max(1, ...) 兜过 bars 数）。 */
export function yFractionScale(vmax, H, padT, padB) {
  const span = H - padT - padB;
  return (v) => (vmax > 0 ? (v / vmax) * span : 0);
}

/** scan 折线图框架的主题色规格。**三个回退值都是空串**：原 drawScanCurve 就是
    `style.getPropertyValue(...).trim()` 无兜底（与 fock.js 的柱状图不同，那边一直
    有回退色）。保持逐字等价，不在此处偷偷加回退 —— tokens.css 缺失时页面本就
    不成立，静默换色只会掩盖问题。 */
export const FRAME_THEME = {
  rule: ["--color-rule", ""],
  ink: ["--color-ink", ""],
  accent: ["--color-accent", ""],
};

/** fock 柱状图的主题色（原 fock.js 的两处 readThemeVars 调用合并到这张表）。 */
export const FOCK_THEME = {
  accent: ["--color-accent", "#2e63d1"],
  error: ["--color-error", "#c33"],
  rule: ["--color-rule", "#ccc"],
  ink: ["--color-ink", "#333"],
};

/** fock joint/batch 热图只需两色。 */
export const FOCK_HEAT_THEME = {
  accent: ["--color-accent", "#2e63d1"],
  error: ["--color-error", "#c33"],
};

/** Wigner 画布的坐标轴叠加色。`paper` 故意**无回退**（空串 → 描边色无效，
    浏览器按 none 处理）—— 原实现就是 `getPropertyValue(...).trim()` 不兜底。 */
export const AXIS_THEME = {
  axis: ["--color-axis", "#7fe0ff"],
  paper: ["--color-paper", ""],
};

/** 轴标签规格：{x, y, anchor, text}。调用方逐条 `el("text", {...})`。
    `fmt`（axisVal）以参数注入，保持本 leaf 零 import。 */
export function axisLabelSpecs({ x0, x1, ylo, yhi, W, H, pad }, fmt) {
  return [
    { x: pad.l, y: H - 4, anchor: "start", text: fmt(x0) },
    { x: W - pad.r, y: H - 4, anchor: "end", text: fmt(x1) },
    { x: pad.l - 6, y: pad.t + 4, anchor: "end", text: fmt(yhi) },
    { x: pad.l - 6, y: H - pad.b, anchor: "end", text: fmt(ylo) },
  ];
}
