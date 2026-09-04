/* 候选 2 — 请求深模块（leaf：零 import，纯函数可 node --test 直测）。
   把 5 处重复的 fetch envelope + seq 丢弃 + busy + 统一错误收敛成一个
   小接口、大行为的深模块。环境依赖（fetch / performance / busy 回调 /
   状态文案）全部由调用方注入，本模块零 DOM、零副作用 —— 这是它能被
   node --test 直接驱动的关键（app.js 0 导出的病根正是副作用内联）。

   契约：
   - validate 失败 → **不发请求**、不置忙、返回 {ok:false,kind:'validate',detail}。
   - busy：进入置 busy(true)，结束（含 stale）一律 busy(false)——每个请求
     都归还自己的占用；同回调下的并发安全由引用计数 busy 保证
     （app.js makeRefCountedBusy：stale 的 busy(false) 只降计数不误清）。
   - 过期成功/失败/网络错误 → 静默丢弃，不调 onOk/onError。
   - 成功 → onOk(body, status)；HTTP 非 2xx → onError({kind:'http',...})；
     fetch reject → onError({kind:'network',...})。 */
"use strict";

/** 单调递增 seq 租约（收编 app.js 的 seqCounter/latestSeq 手写两口）。
    next() 返回当前请求号并推进；isCurrent(n) 判断 n 是否仍是最新。 */
export function createSeqGuard() {
  let cur = 0;
  return {
    next() { return ++cur; },
    current() { return cur; },
    isCurrent(n) { return n === cur; },
  };
}

/** 引用计数 busy：每个请求进入 +1、结束 -1，计数归零才真正切换控件。
    与 requestLab 的“结束一律 busy(false)”契约配套：stale 请求归还自己的
    占用是安全的——同回调下被新请求取代时计数只降一层不误清；跨回调
    （run/sample 组 vs scan 组）互不泄漏（修复 P1 控件卡死）。 */
export function makeRefCountedBusy(apply) {
  let n = 0;
  return (on) => {
    if (on) { if (n === 0) apply(true); n += 1; }
    else { n = Math.max(0, n - 1); if (n === 0) apply(false); }
  };
}

/** 请求枚举/分类。 */
export const REQUEST_KIND = Object.freeze({
  OK: "ok",
  VALIDATE: "validate",
  HTTP: "http",
  NETWORK: "network",
  STALE: "stale",
});

/** 执行一次 POST 请求（深模块：envelope + seq + busy + 错误全在内）。
    opts:
      { payload, seq?, guard?, busy?, validate?, onOk?, onError?,
        fetchImpl?, signal? }
    - guard?+seq?：提供时启用陈旧丢弃；seq 必须是 guard.next() 的返回。
    - busy?(on)：置忙/复原回调（调用方决定禁哪些控件）。
    - validate?(payload)→string?：前置校验，返回错误文案则 abort。
    - onOk?(body, status)：成功（仅当非过期）。
    - onError?(err)：err={kind,detail,status?}（仅当非过期）。
    - fetchImpl?：注入 fetch（测试），缺省全局 fetch。
    - signal?：透传 AbortSignal（本模块不设默认超时，YAGNI）。 */
export async function requestLab(path, opts = {}) {
  const {
    payload,
    seq, guard,
    busy, validate, onOk, onError,
    fetchImpl = globalThis.fetch,
    signal,
  } = opts;

  const stale = () => !!(guard && seq !== undefined) && !guard.isCurrent(seq);

  if (validate) {
    const detail = validate(payload);
    if (detail) return { ok: false, kind: REQUEST_KIND.VALIDATE, detail };
  }

  if (busy) busy(true);
  try {
    const resp = await fetchImpl(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload === undefined ? undefined : JSON.stringify(payload),
      signal,
    });
    /* 过期：静默丢弃，不调 onOk/onError（busy 在 finally 归还）。 */
    if (stale()) return { ok: false, kind: REQUEST_KIND.STALE };
    let body;
    try {
      body = await resp.json();
    } catch {
      body = null;
    }
    if (!resp.ok) {
      const detail = (body && body.detail) || `HTTP ${resp.status}`;
      const err = { kind: REQUEST_KIND.HTTP, detail, status: resp.status };
      if (onError) onError(err);
      return { ok: false, ...err };
    }
    if (onOk) onOk(body, resp.status);
    return { ok: true, kind: REQUEST_KIND.OK, body, status: resp.status };
  } catch (e) {
    /* 网络/其它错误：同样先判过期（过期丢，网络错误交给 onError）。 */
    if (stale()) return { ok: false, kind: REQUEST_KIND.STALE };
    const detail = e && e.message ? e.message : String(e);
    const err = { kind: REQUEST_KIND.NETWORK, detail };
    if (onError) onError(err);
    return { ok: false, ...err };
  } finally {
    /* 无条件归还 busy：stale 请求也归还自己的占用。若用引用计数 busy
       （app.js makeRefCountedBusy），同一个回调下 stale 的 busy(false)
       只是把计数降一层，不会误清仍在跑的新请求——跨回调也互不泄漏。 */
    if (busy) busy(false);
  }
}
