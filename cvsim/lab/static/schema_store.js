/* 票3/4 — /schema 载荷单点 store（leaf，零 import；避免 ops.js↔ops_schema.js
   ESM 循环）。app.js init() 成功拉取后：各消费模块 derive 自己的表并
   写入这里；ops.js toV1Json / editor.js stateFromV1 / palette（票 4
   opsForBackend）运行时读。
   未注入（node --test 旧路径）= null：toV1Json/stateFromV1 回退内置
   常量（表示级事实）；**palette 读口 fail-fast throw**（frozen-graph
   纪律：无 backends 镜像可回退，app.js 失败红条挡板，不静默降级）。 */
"use strict";

let DOC = null;
let TABLES = null;

/** 注入载荷 + 消费方派生表（app.js init() 成功后调用一次）。
    tables: { uiToOp, uiToParam, fockUiToParam, ops }，ops =
    ops_schema.js deriveOps(schema) 产物（UI 名键，票 4）。 */
export function publishSchema(doc, tables) {
  if (!doc || typeof doc !== "object" || !doc.ops) {
    throw new TypeError("/schema 载荷非法（缺 ops）");
  }
  if (!tables || typeof tables !== "object" || !tables.ops) {
    throw new TypeError("派生表非法（缺 ops）");
  }
  DOC = doc;
  TABLES = tables;
}

/** 生效载荷（未注入 = null）。 */
export function schemaDoc() {
  return DOC;
}

/** 生效派生表（{uiToOp, uiToParam, fockUiToParam, ops}；未注入 = null）。 */
export function schemaTables() {
  return TABLES;
}

/** 票 4：backend 工作台托盘（schema 派生，UI 名键序）。
    fail-fast：schema 未注入直接 throw（无静默回退，frozen-graph）。 */
export function opsForBackend(backend) {
  if (!TABLES) {
    throw new Error(
      "palette 未初始化：/schema 拉取失败 — 禁止静默回退（frozen-graph）"
    );
  }
  return Object.keys(TABLES.ops).filter(
    (op) => Array.isArray(TABLES.ops[op].backends) && TABLES.ops[op].backends.includes(backend)
  );
}