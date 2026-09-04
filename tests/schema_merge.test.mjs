/* 票3 — schema 运行时合并纯函数测试 (node --test, zero deps)。
   mergeSchema/deriveOps 消费票 2 `GET /schema` 载荷 (golden 子集手写)，
   产出新 OPS 表：backends/参数形状来自 schema，label/tip/刻度留守，
   v0 源 (vacuum/tmsv/coherent) 原样保留。改名表从 uiName 派生。 */
import test from "node:test";
import assert from "node:assert/strict";

import {
  V0_SOURCES, BASE_OPS, deriveOps, deriveParamRenames,
} from "../cvsim/lab/static/ops_schema.js";

/* ── mock schema fixture：票 2 golden /schema 载荷的手写最小子集 ──
   仅含断言用到的 ops/extensions/initial 键，形状与 assemble_schema()
   输出逐字段一致 (schema.ops[op] = {backends, meta{params}, core_ranges?})。 */
const MOCK_SCHEMA = {
  schema: "cvsim_lab_schema",
  ops: {
    vacuum: { backends: ["gaussian"], meta: { arity: "one", value_kind: { nmode: "int" }, defaults: { nmode: 1 } } },
    tmsv: { backends: ["gaussian"], meta: { arity: "one", value_kind: { r: "num" }, defaults: { r: 0.6 } } },
    coherent: { backends: ["gaussian"], meta: { arity: "one", value_kind: { alpha: "cnum" }, defaults: { alpha: 1 } } },
    squeeze: {
      backends: ["gaussian", "fock", "bosonic"],
      meta: { arity: "one", value_kind: { r: "num", phi: "num" }, defaults: { r: 0.4, phi: 0 } },
    },
    phase: {
      backends: ["gaussian", "fock", "bosonic"],
      meta: { arity: "one", value_kind: { theta: "num" }, defaults: { theta: 1.5707963267948966 } },
    },
    loss: {
      backends: ["gaussian", "fock", "bosonic"],
      meta: { arity: "one", value_kind: { T: "num", nbar: "num" }, defaults: { T: 1.0, nbar: 0 } },
      core_ranges: { T: [0, 1] },
    },
    measure_homodyne: { backends: ["gaussian", "fock", "bosonic"], uiName: "homodyne",
      meta: { arity: "one", value_kind: { phi: "num", name: "string" }, defaults: { phi: 0, name: null } } },
  },
  extensions: {
    cutoff: [1, 30],
    view: { lim_max: 50, lim_min_exclusive: 0, n: [2, 512] },
    sweep: { n: [2, 200] },
    shots: [0, 100000],
    rounds: [1, 100],
  },
  initial: {
    gaussian: null,
    fock: { kind: "int", min: 0 },
    bosonic: { kind: "enum", sources: ["gkp0", "gkp1", "gkp0_2d", "gkp1_2d"], vacuum: null },
  },
};

test("deriveOps: backends 来自 schema (per-op 覆盖)", () => {
  const ops = deriveOps(MOCK_SCHEMA);
  // phase 在 mock 里是三后端；若 schema 改单后端，合并结果跟着变
  assert.deepEqual(ops.phase.backends, ["gaussian", "fock", "bosonic"]);
  assert.deepEqual(ops.homodyne.backends, ["gaussian", "fock", "bosonic"]);
});

test("deriveOps: 参数形状留守 base（票3 实况：meta 无 params 键，review F1 降级）", () => {
  const ops = deriveOps(MOCK_SCHEMA);
  // 票3：参数形状 merge 对真实载荷 inert（golden meta = {arity,value_kind,
  // defaults}）——本断言锁定降级后的实况：base params 原样保留。
  assert.deepEqual(Object.keys(ops.phase.params), ["phi"]);
  assert.deepEqual(Object.keys(ops.loss.params).sort(), ["T", "nbar"]);
  // homodyne 的 meta 无 params 键（golden 形）→ base params 原样
  assert.deepEqual(Object.keys(ops.homodyne.params).sort(), ["name", "phi"]);
  assert.equal(ops.homodyne.params.name.optional, true);   // base 标记留守
  assert.equal(ops.homodyne.params.name.string, true);
});

test("deriveOps: label/tip/刻度/palette 标记留守 base", () => {
  const ops = deriveOps(MOCK_SCHEMA);
  assert.equal(ops.phase.label, "相位");
  assert.ok(ops.phase.tip.includes("相移"));
  assert.equal(ops.phase.params.phi.step, 0.01);
  assert.equal(ops.homodyne.measure, true);
});

test("deriveOps: v0 源 (vacuum/tmsv/coherent) 原样保留（schema 无此三键）", () => {
  const ops = deriveOps(MOCK_SCHEMA);
  for (const s of V0_SOURCES) {
    assert.ok(ops[s], `${s} 保留`);
    assert.deepEqual(ops[s], BASE_OPS[s]);
  }
});

test("deriveOps: 不改 BASE_OPS（纯函数，返回新表）", () => {
  const before = JSON.stringify(BASE_OPS.phase);
  deriveOps(MOCK_SCHEMA);
  assert.equal(JSON.stringify(BASE_OPS.phase), before);
});

test("editor 边界: schema extensions → view/seed/cutoff 校验值", () => {
  const ops = deriveOps(MOCK_SCHEMA);
  assert.equal(ops.__extensions.view.n[1], 512);
  assert.equal(ops.__extensions.cutoff[1], 30);
  assert.equal(ops.__extensions.shots[1], 100000);
});

test("fail-fast: schema.ops 键无 uiName 也无 base 条目 → 合并忽略（不炸）", () => {
  const weird = { ...MOCK_SCHEMA, ops: { ...MOCK_SCHEMA.ops, future_op: { backends: ["fock"], meta: { params: {} } } } };
  const ops = deriveOps(weird);
  assert.ok(!ops.future_op); // 白名单 fail-fast 在 Lab 层，前端只消费子集
});

test("fail-fast: schema 损坏 (无 ops 键) → throw 而非静默空表", () => {
  assert.throws(() => deriveOps({ schema: "cvsim_lab_schema" }), /ops/);
});