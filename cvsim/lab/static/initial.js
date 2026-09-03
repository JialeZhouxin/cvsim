/* Gaussian Lab L2 — initial 字段单点语义（F7/B6, per-backend）。
   `initial` 是 per-mode 初始态扩展字段，语义按 backend 二分：
   fock = 每模光子数（非负整数，0 = 真空，缺省全 0）；
   bosonic = 每模 GKP 源名（null = 真空，gkp0/gkp1/gkp0_2d/gkp1_2d）；
   gaussian = 无此字段。两套值互不兼容——切换 backend 必须经
   remapForBackend 重映射，直接复用旧值会被服务端 422 拒收
   （"initial must be a list of null/'gkp0'/..."）。
   纯函数 + 常量表，零 DOM / 零依赖（node --test 可测）。 */
"use strict";

//: bosonic 每模合法源名（与 ir.py _load_bosonic 白名单一致；null = 真空）。
export const BOSONIC_SOURCES = Object.freeze(["gkp0", "gkp1", "gkp0_2d", "gkp1_2d"]);

//: bosonic 每模下拉框选项 [value, label]（value null → "" 占位，渲染层翻译）。
export const BOSONIC_SOURCE_OPTIONS = Object.freeze([
  [null, "真空"],
  ["gkp0", "gkp0"],
  ["gkp1", "gkp1"],
  ["gkp0_2d", "gkp0_2d(Z基)"],
  ["gkp1_2d", "gkp1_2d(Z基)"],
]);

//: initial 是否是 backend 语义下的合法单项（payload 值层面，不含长度）。
function itemOk(backend, item) {
  if (backend === "fock") {
    return Number.isInteger(item) && item >= 0;
  }
  return item === null || BOSONIC_SOURCES.includes(item);
}

/** payload.initial → editor state.initial（backend 语义校验）。
    undefined/null → null（缺省 = 全真空，旧 JSON 零破坏）。
    返回 {initial} 或 {error}（中文报错，UI 直接显示）。 */
export function parseInitial(backend, payload, nmode) {
  if (payload === undefined || payload === null) return { initial: null };
  if (!Array.isArray(payload) || payload.length !== nmode) {
    return { error: `initial 必须是长度为 ${nmode} 的数组` };
  }
  const bad = payload.some((n) => !itemOk(backend, n));
  if (bad) {
    return {
      error: backend === "fock"
        ? `initial 必须是 ${nmode} 个非负整数`
        : `initial 每项只能是 null / ${BOSONIC_SOURCES.join(" / ")}`,
    };
  }
  return { initial: [...payload] };
}

/** editor state.initial → payload.initial（按 backend 语义裁剪 + 缺省省略）。
    防御纪律：非法项（跨后端残留）不外泄——写不出全合法值宁可不写字段
    （缺省即真空），类型错误交给服务端把守。 */
export function serializeInitial(backend, initial, nmode) {
  if (backend === "gaussian") return undefined; // gaussian 无 initial 字段
  if (!Array.isArray(initial)) return undefined; // null = 全真空，不写
  const out = initial.slice(0, nmode);
  const okItem = backend === "fock"
    ? ((v) => Number.isInteger(v) && v >= 0)
    : ((v) => v === null || BOSONIC_SOURCES.includes(v));
  if (!out.every(okItem)) return undefined; // 跨后端残留：不写非法 payload
  const empty = backend === "fock"
    ? out.every((n) => n === 0)
    : out.every((v) => v === null);
  return empty ? undefined : out; // 非全真空才写（缺省不写 = 旧 JSON 字节不变）
}

/** backend 切换时的语义重映射（Q2=B 决策）。
    真空对应项保留（fock 0 ↔ bosonic null，物理同为真空初态）；
    非真空项没有跨表示对应物，重置为真空并计数——UI 用返回的 reset 数
    提示"N 项初始态因后端切换被重置"，永不静默截断。 */
export function remapForBackend(from, to, initial, nmode) {
  const out = Array(nmode).fill(to === "bosonic" ? null : 0);
  let reset = 0;
  for (let i = 0; i < nmode; i++) {
    const v = Array.isArray(initial) ? initial[i] : undefined;
    if (v === undefined) continue;
    if (from === to) { out[i] = v; continue; } // 同后端（加模 pad 等）：原值保留
    if (from === "gaussian") continue; // 无旧语义，保持缺省真空
    // fock ↔ bosonic：真空对应项保留，其余重置计数
    const vacuum = from === "bosonic" ? v === null : (v === 0 || v === null);
    if (!vacuum) reset++; // out[i] 保持缺省真空，由调用方提示重置数
  }
  return { initial: out, reset };
}

/** backend 的“真空”占位值：bosonic 源名语义 = null，fock 整数语义 = 0，
    gaussian 无 initial 字段（返回 0 无害占位）。 */
export function vacuumDefault(backend) {
  return backend === "bosonic" ? null : 0;
}

/** 初始态输入控件的渲染缓存键：backend + 模数。
    旧键只有模数 → 切换 backend 后模数不变，控件早退不刷新
    （bosonic 下残留 fock 数字输入框的伴生 bug）。 */
export function initialCacheKey(backend, nmode) {
  return `${backend}:${nmode}`;
}