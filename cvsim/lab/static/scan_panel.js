/* Gaussian Lab — scan 面板纯查询逻辑 leaf（review §3.3 #3，ADR-0009）。
   app.js 的 scan 段把 OPS 表查询与 DOM 读写混在一起；本 leaf 收走**查询**
   那半：可 sweep 节点集合、脏键、参数键、自适应量程。DOM 读写（<option>
   重建、note 文案、按钮 disabled、SVG 绘制）留在 app.js。

   零 import、零 DOM（OPS 表以参数注入）：node --test 直测
   （tests/scan_panel.test.mjs）。 */
"use strict";

/** 该节点是否可 sweep：任一参数带 `sweep:[min,max]` 元数据。 */
export function isSweepable(node, ops) {
  return Object.values(ops[node.op]?.params || {}).some((d) => Array.isArray(d.sweep));
}

/** 可 sweep 节点列表（保序）。`ops` 表由调用方注入。 */
export function sweepableNodes(state, ops) {
  return state.nodes.filter((n) => isSweepable(n, ops));
}

/** C1 R2: 脏键 = 「可 sweep 节点身份集合」+ nmode，**不是 nodes 数组引用**。

    引用比较不可能命中：onParam 用 `state.nodes.map(...)` 重构数组，map 无论
    元素是否变化都返回新数组，故每次滑条事件都是新引用 → 永不早退（实测：
    代码看似改了、行为完全没变）。这里只取列表真正依赖的东西 —— 哪些节点可
    sweep 即其 (id, op)，参数**值**不进列表。故拖滑条（id/op 不变）命中早退，
    增删节点 / 改 op / 增删模（都在键里）则重建。 */
export function scanNodeListKey(state, ops) {
  const sig = sweepableNodes(state, ops)
    .map((n) => `${n.id}:${n.op}`)
    .join(",");
  return `${state.nmode}|${sig}`;
}

/** 该节点可 sweep 的参数键（保序）。节点缺失 / 无 meta → 空数组。 */
export function sweepParamKeys(node, ops) {
  const meta = node && ops[node.op];
  if (!meta) return [];
  return Object.keys(meta.params).filter((k) => Array.isArray(meta.params[k].sweep));
}

/** 自适应量程：参数元数据的 `sweep:[min,max]` → {min, max, n}；
    无 sweep 元数据 → null（调用方保持现输入）。 */
export function sweepDefaults(node, param, ops) {
  const d = node && ops[node.op]?.params?.[param];
  if (!d || !Array.isArray(d.sweep)) return null;
  return { min: d.sweep[0], max: d.sweep[1], n: 50 };
}

/** modes_A 下拉的选项值：1 .. nmode-1（E_N 需至少 2 模）。
    nmode < 2 → 空数组（调用方据此禁用按钮 + 显提示）。 */
export function modesAOptions(nmode) {
  const out = [];
  for (let k = 1; k <= nmode - 1; k++) out.push({ value: String(k), label: `[0..${k - 1}]` });
  return out;
}

/** scan 按钮可用性：nmode>=2 且列表非空。 */
export function scanEnabled(nmode, nodeCount) {
  return nmode >= 2 && nodeCount > 0;
}
