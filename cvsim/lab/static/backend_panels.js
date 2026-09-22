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
};

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
