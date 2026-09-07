/* 票3 — Lab 默认场景单一事实源 (leaf: 零 import 零 DOM; ADR-0009)。
   L5.5 默认场景：两个真空模 + 两个位移器（coherent 态两路）@ x=0。
   消费方：app.js (initEditor defaultScene) + test_lab_ui.py (经 node
   子进程 JSON.stringify 取值 —— 测试不再正则读 app.js 源码)。 */
"use strict";

export const DEFAULT_SCENE = {
  schema: "circuit_v1",
  seed: 0,
  nmode: 2,
  ops: [
    { id: "d0", op: "displace", modes: [0], params: { alpha: [1.0, 0.0] } },
    { id: "d1", op: "displace", modes: [1], params: { alpha: [1.0, 0.0] } },
  ],
  view: { wigner_mode: 0, lim: 5.0, n: 64 },
  ui: { staff: { d0: 0, d1: 0 } },
};
