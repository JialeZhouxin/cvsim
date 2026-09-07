/* 票3 — Lab 默认场景单一事实源 (leaf: 零 import 零 DOM; ADR-0009)。
   L5.5 默认场景：两个真空模 + 两个位移器（coherent 态两路）@ x=0。
   消费方：app.js (initEditor defaultScene) + test_lab_ui.py (经 node
   子进程 JSON.stringify 取值 —— 测试不再正则读 app.js 源码)。 */
"use strict";

export const DEFAULT_SCENE = {
  schema: "circuit_v0",
  seed: 0,
  nodes: [
    { id: "s0", op: "vacuum", params: { nmode: 1 } },
    { id: "s1", op: "vacuum", params: { nmode: 1 } },
    { id: "d0", op: "displace", params: { alpha: 1.0 }, mode: 0, ui: { x: 0 } },
    { id: "d1", op: "displace", params: { alpha: 1.0 }, mode: 1, ui: { x: 0 } },
  ],
  edges: [],
  view: { wigner_mode: 0, lim: 5.0, n: 64 },
  ui: {},
};
