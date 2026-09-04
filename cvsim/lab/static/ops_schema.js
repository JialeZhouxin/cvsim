/* 票3 — schema 运行时合并层（GET /schema 消费端，单一事实源）。
   **票3 实况（review F1）**：票 2 golden meta 无 params 键（{arity,
   value_kind, defaults}），deriveOps 的参数形状合并在真实载荷上
   **inert**——本文件的 derive* 纯函数是票 4 收编项（schema 扩
   per-op params 或消费方改读 value_kind 时激活）；票 3 运行时真正
   派生的只有：editor.js deriveEditorTables（改名/边界）与
   initial.js mergeInitialSchema（名单）。app.js 经 schema_store.js
   注入的 tables 亦只含这三类。BASE_OPS 再导出供测试对照。

   纯函数（收 schema 参数返回新表，不改 BASE_OPS），node --test 注入 mock
   fixture 直测（zero-dep）。store: schema_store.js（leaf，防循环）。 */
"use strict";

import { OPS as BASE_OPS } from "./ops.js";

//: BASE_OPS 再导出（测试消费 base 键集；不改 ops.js 导出面）。
export { BASE_OPS };
import { BOSONIC_SOURCES, BOSONIC_SOURCE_OPTIONS } from "./initial.js";

//: v0 源（UI 概念，schema 无此三键；载入旧 JSON 兼容，palette 纪律不变）。
export const V0_SOURCES = Object.freeze(["vacuum", "tmsv", "coherent"]);

//: schema 载荷单点在 schema_store.js（leaf）；此处只留派生纯函数。

/** schema 载荷 → 合并后的 OPS 表（纯函数）。
    - schema 键 = IR 名；本表键 = UI 名（`uiName || op`，票 2 Q3 同名省略）。
    - IR 名在 schema 有而 base 无 → 忽略（Lab 白名单 fail-fast 已挡；
      前端只消费子集，UI 控件未建前不出托盘）。
    - base 键在 schema 无（v0 源/未来 JSON-only op）→ 原样保留。 */
export function deriveOps(schema) {
  if (!schema || typeof schema !== "object" || !schema.ops) {
    throw new TypeError("schema 载荷非法（缺 ops）");
  }
  const irToUi = {};
  for (const [ir, entry] of Object.entries(schema.ops)) {
    irToUi[ir] = entry.uiName || ir;
  }
  const out = {};
  // pass 1: base 条目全部保留（含 v0 源 + schema 未列的 JSON-only op）
  for (const [ui, meta] of Object.entries(BASE_OPS)) {
    out[ui] = meta;
  }
  // pass 2: schema 覆盖（per-op backends；参数形状仅当 meta.params 存在——
  // 票 3 实况（review F1）：golden meta 无 params 键，此时 base 参数形状
  // 原样保留（label/tip/刻度/advanced/sweep 全留守）；票 4 schema 扩
  // per-op params 时本分支自然激活）。
  for (const [ir, entry] of Object.entries(schema.ops)) {
    const ui = irToUi[ir];
    const base = Object.hasOwn(BASE_OPS, ui) ? BASE_OPS[ui] : null;
    if (!base) continue; // 无 UI 控件的 IR op：schema 里有、UI 不管
    const merged = { ...base, backends: [...entry.backends] };
    const schemaParams = entry.meta?.params ?? null;
    if (schemaParams) {
      const params = {};
      for (const [pk, pmeta] of Object.entries(schemaParams)) {
        const uk = matchUiParam(base, ir, ui, pk);
        const basep = base.params[uk] ?? {};
        params[uk] = { ...basep };
        if (pmeta.required === false) params[uk].optional = true;
        if (pmeta.kind === "string") params[uk].string = true;
      }
      merged.params = params;
    }
    out[ui] = merged;
  }
  // extensions 附载（editor.js 校验读这里，不再手写 [2,512] 等）
  out.__extensions = structuredClone(schema.extensions ?? {});
  out.__initial = structuredClone(schema.initial ?? {});
  return out;
}
/** UI↔IR 参数改名派生（票 4 收编项——真实 golden meta 无 params 键，
    本函数现只在 schema_merge.test.mjs 的 mock（含 meta.params）上有义；
    保留为 schema 扩 per-op params 时的激活点。 */
export function deriveParamRenames(schema) {
  const v1ToUi = {};
  const uiToV1 = {};
  const fockDrop = {};
  for (const [ir, entry] of Object.entries(schema.ops)) {
    const ui = entry.uiName || ir;
    const irParams = Object.keys(entry.meta?.params ?? {});
    const base = Object.hasOwn(BASE_OPS, ui) ? BASE_OPS[ui] : null;
    if (!base) continue;
    for (const ip of irParams) {
      const up = matchUiParam(base, ir, ui, ip);
      if (!Object.hasOwn(base.params, up)) {
        (fockDrop[ir] ??= new Set()).add(up);
        continue;
      }
      if (up !== ip) {
        (v1ToUi[ir] ??= {})[ip] = up;
        (uiToV1[ui] ??= {})[up] = ip;
      }
    }
  }
  return { v1ToUi, uiToV1, fockDrop };
}
