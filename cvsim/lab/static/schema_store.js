/* 票3 — /schema 载荷单点 store（leaf，零 import；避免 ops.js↔ops_schema.js
   ESM 循环）。app.js init() 成功拉取后：各消费模块 derive 自己的表并
   写入这里；ops.js toV1Json / editor.js stateFromV1 运行时读。
   未注入（node --test 旧路径）= null，消费方回退内置常量（app.js
   schema 必到：失败红条挡板，不静默降级）。 */
"use strict";

let DOC = null;
let TABLES = null;

/** 注入载荷 + 消费方派生表（app.js init() 成功后调用一次）。 */
export function publishSchema(doc, tables) {
  if (!doc || typeof doc !== "object" || !doc.ops) {
    throw new TypeError("/schema 载荷非法（缺 ops）");
  }
  DOC = doc;
  TABLES = tables;
}

/** 生效载荷（未注入 = null）。 */
export function schemaDoc() {
  return DOC;
}

/** 生效派生表（{uiToV1Param, irToUiOp, fockUiToV1Param}；未注入 = null）。 */
export function schemaTables() {
  return TABLES;
}