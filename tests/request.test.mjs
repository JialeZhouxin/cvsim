/* 候选 2 — requestLab 深模块契约测试 (node --test, zero deps).
   锁：validate 先跑并发请求、过期响应静默丢弃（不动 busy/onOk/onError）、
   HTTP/网络错误分类、成功 onOk 只调一次、busy on/off 对偶。fetch 注入。 */
import test from "node:test";
import assert from "node:assert/strict";

import { createSeqGuard, requestLab, makeRefCountedBusy } from "../cvsim/lab/static/request.js";

/* fetch 可注入 stub：返回预置 Response-like 或 reject。 */
function okBody(obj) {
  return { ok: true, status: 200, json: async () => obj };
}
function errBody(status, detail) {
  return { ok: false, status, json: async () => ({ detail }) };
}

test("validate 失败 → 不发请求、不置忙，返回 kind=validate", async () => {
  let fetched = false;
  let busyCalls = 0;
  const res = await requestLab("/run", {
    payload: { seed: -1 },
    fetchImpl: async () => { fetched = true; return okBody({}); },
    busy: () => { busyCalls += 1; },
    validate: () => "seed 必须是非负整数",
  });
  assert.equal(fetched, false);
  assert.equal(busyCalls, 0);
  assert.equal(res.ok, false);
  assert.equal(res.kind, "validate");
  assert.equal(res.detail, "seed 必须是非负整数");
});

test("成功 → busy(true) 再 busy(false)，onOk 收 body+status", async () => {
  const busySeq = [];
  let onOkArgs = null;
  const body = { nmode: 2 };
  const res = await requestLab("/run", {
    payload: {},
    busy: (on) => busySeq.push(on),
    onOk: (b, status) => { onOkArgs = [b, status]; },
    onError: () => { throw new Error("onError should not fire"); },
    fetchImpl: async () => okBody(body),
  });
  assert.deepEqual(busySeq, [true, false]);
  assert.equal(res.ok, true);
  assert.equal(res.kind, "ok");
  assert.equal(res.status, 200);
  assert.equal(res.body, body);
  assert.deepEqual(onOkArgs, [body, 200]);
});

test("HTTP 非 2xx → onError({kind:http}),busy 复原，返回 kind=http", async () => {
  const busySeq = [];
  let errArgs = null;
  const res = await requestLab("/run", {
    payload: {},
    busy: (on) => busySeq.push(on),
    onError: (e) => { errArgs = e; },
    fetchImpl: async () => errBody(422, "op 'x' not in Lab whitelist"),
  });
  assert.deepEqual(busySeq, [true, false]);
  assert.equal(res.ok, false);
  assert.equal(res.kind, "http");
  assert.equal(res.status, 422);
  assert.equal(res.detail, "op 'x' not in Lab whitelist");
  assert.deepEqual(errArgs, { kind: "http", detail: "op 'x' not in Lab whitelist", status: 422 });
});

test("网络 reject → onError({kind:network}),busy 复原", async () => {
  const busySeq = [];
  let errArgs = null;
  const res = await requestLab("/run", {
    payload: {},
    busy: (on) => busySeq.push(on),
    onError: (e) => { errArgs = e; },
    fetchImpl: async () => { throw new Error("network down"); },
  });
  assert.deepEqual(busySeq, [true, false]);
  assert.equal(res.ok, false);
  assert.equal(res.kind, "network");
  assert.equal(res.detail, "network down");
  assert.equal(errArgs.kind, "network");
});

test("过期成功响应 → 静默丢弃（不调 onOk，busy 仍归还）", async () => {
  const guard = createSeqGuard();
  const s1 = guard.next(); // 旧请求
  guard.next();            // 更新请求取代它
  let busySeq = [];
  let onOk = 0;
  const res = await requestLab("/run", {
    payload: {}, seq: s1, guard,
    busy: (on) => busySeq.push(on),
    onOk: () => { onOk += 1; },
    fetchImpl: async () => okBody({}),
  });
  assert.equal(res.ok, false);
  assert.equal(res.kind, "stale");
  assert.equal(onOk, 0);
  assert.deepEqual(busySeq, [true, false]); // P1 修复：stale 也归还 busy（引用计数下安全）
});

test("过期网络错误 → 静默丢弃（不调 onError）", async () => {
  const guard = createSeqGuard();
  const s1 = guard.next();
  guard.next();
  let onErr = 0;
  const res = await requestLab("/run", {
    payload: {}, seq: s1, guard,
    onError: () => { onErr += 1; },
    fetchImpl: async () => { throw new Error("late failure"); },
  });
  assert.equal(res.ok, false);
  assert.equal(res.kind, "stale");
  assert.equal(onErr, 0);
});

test("seqGuard：next 自增 + isCurrent 只在最新", () => {
  const g = createSeqGuard();
  assert.equal(g.current(), 0);
  const a = g.next();
  assert.equal(a, 1);
  assert.equal(g.isCurrent(a), true);
  const b = g.next();
  assert.equal(b, 2);
  assert.equal(g.isCurrent(a), false);
  assert.equal(g.isCurrent(b), true);
  assert.equal(g.current(), 2);
});

test("makeRefCountedBusy：计数归零才 apply(false)，stale 归还不误清新请求", () => {
  const seq = [];
  const busy = makeRefCountedBusy((on) => seq.push(on));
  busy(true);  // 请求 A 进入
  busy(true);  // 请求 B 进入（同回调，B 取代 A）
  assert.deepEqual(seq, [true]);      // 首次进入才真正 apply(true)
  busy(false); // A stale，归还自己的占用
  assert.deepEqual(seq, [true]);      // 计数 2→1，未归零 → 不 apply(false)，不误清 B
  busy(false); // B 结束
  assert.deepEqual(seq, [true, false]); // 计数归零 → apply(false)
});

test("makeRefCountedBusy：跨回调互不泄漏（P1 场景：run 组 vs scan 组）", () => {
  const applied = [];
  const runGrp = makeRefCountedBusy((on) => applied.push(["run", on]));
  const scanGrp = makeRefCountedBusy((on) => applied.push(["scan", on]));
  runGrp(true);   // run 开始
  scanGrp(true);  // scan 开始（run 变 stale）
  scanGrp(false); // scan 结束，只影响 scan 组
  assert.deepEqual(applied, [["run", true], ["scan", true], ["scan", false]]); // run 组未被动
  runGrp(false);  // run 结束
  assert.deepEqual(applied, [["run", true], ["scan", true], ["scan", false], ["run", false]]);
});
