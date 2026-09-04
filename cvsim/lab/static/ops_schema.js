/* 票3/4 — schema 运行时合并层（GET /schema 消费端，单一事实源）。
   票 4 实况：deriveOps 已接线（app.js init() 发布进 schema_store，
   backendOps 经 opsForBackend 读派生表）——backends 字段从 schema
   派生，ops.js 手写 backends 字段已删。参数形状 merge 仍 inert
   （golden meta 无 params 键，锁定 descope 不加键；本分支为未来
   激活点，见 deriveOps pass2 注释）。改名表：
   deriveParamRenames 同为纯函数 + 测试（激活点同上）；运行时改名
   表（表示级差异 loss T→eta / squeeze phi drop）按票 3 锁定决策
   保留在 deriveEditorTables（editor.js）。BASE_OPS 再导出供测试对照。

   纯函数（收 schema 参数返回新表，不改 BASE_OPS），node --test 注入 mock
   fixture 直测（zero-dep）。store: schema_store.js（leaf，防循环）。 */
"use strict";

import { OPS as BASE_OPS } from "./ops.js";

//: BASE_OPS 再导出（测试消费 base 键集；不改 ops.js 导出面）。
export { BASE_OPS };

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
  // pass 1: base 条目全部保留（含 v0 源 + schema 未列的 JSON-only op）。
  // 票 4：v0 源补 backends: ["gaussian"] —— 结构事实（v0 源仅在
  // gaussian 工作台存在，frozen-graph 下无回退），非镜像；
  // schema 未列的其它 base 键同样补 ["gaussian"]（当前无此类，
  // 未来 JSON-only op 落此默认，UI 元数据行可覆盖）。
  for (const [ui, meta] of Object.entries(BASE_OPS)) {
    out[ui] = { ...meta, backends: ["gaussian"] };
  }
  // pass 2: schema 覆盖（per-op backends；参数形状仅当 meta.params 存在——
  // 票 3 实况（review F1）：golden meta 无 params 键，此时 base 参数形状
  // 原样保留（label/tip/刻度/advanced/sweep 全留守）；本分支维持为
  // schema 扩 per-op params 时的激活点（锁定 descope，不加键）。
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
