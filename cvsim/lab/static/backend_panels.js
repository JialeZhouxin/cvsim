/* Gaussian Lab — per-backend 差异知识 leaf（review §3.3 #1，ADR-0009）。
   后端差异此前散在 4 张表 + 23 处条件分支里（initial.js 9、editor.js 6、
   ops.js 5、staff.js 2、app.js 2），而 app.js 的注释自称那里是"单点"。
   本 leaf 收的是**表驱动的那部分**：面板可见性、meter 行、run 请求体扩展、
   initial 输入类型。新后端 = 加一行，不添 if。

   零 import、零 DOM：node --test 直测（tests/backend_panels.test.mjs）。
   各表示自身语义的分支（initial.js 的取值合法性、ops.js 的序列化、
   editor.js 的校验边界）留在原处 —— 那些是表示知识，不是"后端差异表"。 */
"use strict";

/** R7 (ADR-0008 follow-up)：面板可见性表。id → 是否可见。
    syncBackendPanels 的唯一消费者。 */
export const BACKEND_PANELS = {
  gaussian: { "scan-panel": true, "state-grid": true, "fock-panel": false, "fock-charts": false, "bosonic-panel": false, "meters-panel": true, "wigner-side": true },
  fock: { "scan-panel": false, "state-grid": false, "fock-panel": true, "fock-charts": true, "bosonic-panel": false, "meters-panel": false, "wigner-side": false },
  bosonic: { "scan-panel": false, "state-grid": false, "fock-panel": false, "fock-charts": false, "bosonic-panel": true, "meters-panel": true, "wigner-side": true },
};

/** 未知 backend → undefined（调用方保持现状，防御不摸 DOM；schema 门先拦）。 */
export function panelsFor(backend) {
  return BACKEND_PANELS[backend];
}

/** R6 (ADR-0008 决策 3)：meter 行标签 — 值消费者（meter VALUE 读取口）与
    渲染顺序的唯一前端声明处；**键集**来自 /schema meter 矩阵
    （schema_store.meterKeys，后端事实源 cvsim/lab/result.py）。 */
export const METER_ROWS = {
  purity: { value: "m-purity", label: "纯度" },
  mean_photon: { value: "m-nbar", label: "平均光子数" },
  mean_photon_per_mode: { value: "m-permode", label: "各模式 ⟨n⟩" },
  log_negativity: { value: "m-logneg", label: "对数负度" },
  duan_sum: { value: "m-duan", label: "Duan 和 (纠缠 < 2)" },
};

/** R8: 跨模 Wigner 平面的**呈现**表（键 → 中文标签）。键集**不**在这里 ——
    键集来自 /schema `extensions.view.planes`（后端事实源
    `cvsim/lab/schema.py::_EXTENSIONS["view"]["planes"]`），同 METER_ROWS 与
    meterKeys 的分工：静态表管标签，schema 管键集与顺序。 */
export const PLANE_LABELS = {
  single: "单模 (x, p)",
  xx: "x–x 平面",
  pp: "p–p 平面",
  epr: "EPR 平面 (x₋, p₊)",
};

/** R8: 平面下拉的纯渲染计划 —— schema 的 `planes` 列表 → 逐项 {value, label}。
    顺序取 schema（后端是事实源），标签取静态表、缺失则回落原始键名（不静默丢弃：
    后端新加一个预设时前端仍能选到，只是暂时显示英文键名）。 */
export function planeOptions(planes) {
  return (Array.isArray(planes) ? planes : []).map((value) => ({
    value,
    label: PLANE_LABELS[value] ?? value,
  }));
}

/** R8: pair 控件是否该出现。只有 gaussian 且 plane != single 且至少两模时
    模对才有意义 —— single 不用 pair，fock/bosonic 后端直接 422。 */
export function showPairControls(backend, plane, nmode) {
  return backend === "gaussian" && plane !== "single" && nmode >= 2;
}

/** R8/S11: 热图轴名计划 → `[水平轴名, 垂直轴名]`。

    优先用后端给的 `wigner.axes.labels`（跨模平面：后端才是分量组合的事实源，
    前端**不得**重推物理，design D5）。没有 `axes` 就是单模的 (x, p) —— 后端
    **不能**给单模发这个键：`tests/test_lab_golden.py` 深比对 `body == golden`，
    多一个键即值漂移，而 9 个 golden 禁止重捕；AC7 也明写 single 必须保持字节兼容。
    所以单模轴名在此**前端合成**。

    带 mode 下标（`x1`/`p1`）而不是裸 `x`/`p`：nmode≥2 时 mode 选择器就在旁边，
    不写下标会指不明是哪一模，且与跨模平面的 `x0`/`x2` 风格一致。

    `mode` 非有限数时回落 0（`render` 的调用方可能没带 wigner_mode）。 */
export function axisLabelPlan(wigner, mode) {
  const labels = wigner && wigner.axes ? wigner.axes.labels : null;
  if (Array.isArray(labels) && labels.length === 2) return labels;
  const m = Number.isFinite(mode) ? mode : 0;
  return [`x${m}`, `p${m}`];
}

/** meter 面板的纯渲染计划：矩阵键集 → 逐行 {可见?、行 id、值 id}。

    矩阵定行可见性（矩阵外的静态行隐藏）；flag 型扩展键（singular）不占
    meter 行 —— 其专属消费者在 showMeasurement（m-singular-note）。 */
export function meterRowPlan(keys) {
  return Object.entries(METER_ROWS).map(([key, row]) => ({
    key,
    rowId: `m-row-${key}`,
    valueId: row.value,
    label: row.label,
    visible: keys.has(key),
  }));
}

/** R7：per-backend run 请求体扩展 —— bosonic 一次拉全部分步快照（断点中间态）；
    gaussian/fock 无扩展。知识单点（原三元式散在 doRun）。 */
export const RUN_BODY_EXTENSIONS = {
  bosonic: { detail: "steps" },
};

/** run 请求体扩展；无扩展的后端 → 空对象（可安全展开）。 */
export function runBodyExtensions(backend) {
  return RUN_BODY_EXTENSIONS[backend] ?? {};
}

/** R7：per-backend 初始态输入配置 — int = fock 光子数输入（cutoff 上限联动，
    syncFockInputValues）；enum = bosonic 源名下拉（renderBosonicInitial）；
    undefined = 无 initial 字段（gaussian——卡片隐藏）。 */
export const INITIAL_INPUT_KIND = { fock: "int", bosonic: "enum" };

/** initial 输入控件类型；gaussian → undefined（无 initial 字段）。 */
export function initialInputKind(backend) {
  return INITIAL_INPUT_KIND[backend];
}
