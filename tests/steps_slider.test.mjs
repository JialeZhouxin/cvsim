/* 票C — steps_slider leaf 契约测试 (node --test, zero deps, ADR-0009)。
   滑条状态机（空/越界/非有限保底）+ 三文案函数各形态。
   stepMeters 以注入 fmtFn 测试（叶子零 import：测试里传真实 fmt 的
   等价 stub，锁「缺失键 → —」经 fmtFn 兜底的语义）。 */
import test from "node:test";
import assert from "node:assert/strict";

import { initStepState, stepLabel, stepDesc, stepMeters } from "../cvsim/lab/static/steps_slider.js";

/* fmt 的语义等价 stub（与 svg_kit.js fmt 同语义，避免跨 leaf import）：
   非有限/非 number → "—"，else toPrecision(5)。 */
const fmtLike = (x) =>
  (typeof x !== "number" || !Number.isFinite(x)) ? "—" : x.toPrecision(5);

/* ── initStepState ───────────────────────────────────────── */

test("initStepState：空数组 → disabled:true, max:0, value:0", () => {
  assert.deepEqual(initStepState([], 3), { max: 0, value: 0, disabled: true });
});

test("initStepState：非数组（undefined/null）→ disabled", () => {
  assert.deepEqual(initStepState(undefined, 2), { max: 0, value: 0, disabled: true });
  assert.deepEqual(initStepState(null, 2), { max: 0, value: 0, disabled: true });
});

test("initStepState：正常 steps → max = length-1，value 保持原值", () => {
  const steps = [{ op: "x" }, { op: "y" }, { op: "z" }];
  assert.deepEqual(initStepState(steps, 1), { max: 2, value: 1, disabled: false });
});

test("initStepState：value 越界（≥ length）→ 保底最后一步（滑条停在末尾选最终态）", () => {
  const steps = [{ op: "x" }, { op: "y" }, { op: "z" }];
  assert.deepEqual(initStepState(steps, 3), { max: 2, value: 2, disabled: false });
  assert.deepEqual(initStepState(steps, 99), { max: 2, value: 2, disabled: false });
});

test("initStepState：prevValue 非有限（NaN/undefined/空串）→ 保底最后一步", () => {
  const steps = [{ op: "x" }, { op: "y" }, { op: "z" }];
  assert.deepEqual(initStepState(steps, NaN), { max: 2, value: 2, disabled: false });
  assert.deepEqual(initStepState(steps, undefined), { max: 2, value: 2, disabled: false });
  assert.deepEqual(initStepState(steps, ""), { max: 2, value: 2, disabled: false });
});

test("initStepState：字符串数字取整（slider.value 是字符串）", () => {
  const steps = [{ op: "x" }, { op: "y" }, { op: "z" }];
  assert.equal(initStepState(steps, "1").value, 1);
});

/* ── stepLabel ───────────────────────────────────────────── */

test("stepLabel：step k/N 文案逐字（N = 末步下标）", () => {
  const steps = [{ op: "x" }, { op: "y" }, { op: "z" }];
  assert.equal(stepLabel(0, steps), "step 0/2");
  assert.equal(stepLabel(2, steps), "step 2/2");
});

/* ── stepDesc ────────────────────────────────────────────── */

test("stepDesc：measure_ 前缀 → measure·，其余 _ → 空格", () => {
  assert.equal(stepDesc("measure_x"), "measure·x");
  assert.equal(stepDesc("measure_p"), "measure·p");
  assert.equal(stepDesc("phase_shift"), "phase shift");
});

test("stepDesc：无下划线 op 原样", () => {
  assert.equal(stepDesc("tmsv"), "tmsv");
});

/* ── stepMeters ──────────────────────────────────────────── */

test("stepMeters：双键齐全 → 模板双空格分隔，fmtFn 五位有效数字", () => {
  const meters = { mean_photon: 1.5, purity: 0.987654 };
  assert.equal(stepMeters(meters, fmtLike), "⟨n⟩ 1.5000  ·  purity 0.98765");
});

test("stepMeters：缺失键 → fmtFn(undefined) → —（诚实缺失）", () => {
  assert.equal(stepMeters({}, fmtLike), "⟨n⟩ —  ·  purity —");
});

test("stepMeters：meters 本身缺失（s.meters 为 undefined）→ 双 —", () => {
  assert.equal(stepMeters(undefined, fmtLike), "⟨n⟩ —  ·  purity —");
});