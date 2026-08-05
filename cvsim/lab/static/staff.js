/* Gaussian Lab L5 — staff (五线谱) editor view.
   Pure layout logic (staffLayout) is ESM-exported for node --test;
   DOM/DnD work lives only inside initStaff. */
"use strict";

import { OPS, sourceRows } from "./ops.js";

export const GATE_W = 72;   // px per x unit (gate cell width)
export const ROW_H = 56;    // px per lane
export const SRC_W = 132;   // px source column

/** Pure: state → staff geometry. rows: one per mode (lane), each tagged with
    its source; gates: placed ops with span for two-mode crossing. */
export function staffLayout(state) {
  const rows = [];
  for (const r of sourceRows(state.nodes)) {
    for (let m = r.modeStart; m < r.modeEnd; m++) {
      rows.push({
        mode: m, srcId: r.srcId, srcOp: r.op, srcParams: r.params,
        srcFirst: m === r.modeStart, srcLast: m === r.modeEnd - 1,
      });
    }
  }
  const gates = [];
  for (const n of state.nodes) {
    const meta = OPS[n.op];
    if (!meta || meta.kind === "source") continue;
    const two = meta.kind === "two";
    const modeA = two ? n.modes[0] : n.mode;
    const modeB = two ? n.modes[1] : n.mode;
    gates.push({ node: n, two, modeA, modeB, span: Math.abs(modeB - modeA) + 1, top: Math.min(modeA, modeB), x: n.ui?.x ?? 0 });
  }
  return { rows, gates, nmode: rows.length };
}

/** DOM wiring (browser only). api: {getState, onPlace, onCompletePlacing,
    onMove, onDelete, onParam, onPickSweep, onStatus}. */
export function initStaff(root, api) {
  let placing = null; // {op, modeA, x} — two-mode "pick second lane" state

  function render() {
    closeCard();
    const { rows, gates, nmode } = staffLayout(api.getState());
    root.replaceChildren();
    root.className = "staff";

    const grid = document.createElement("div");
    grid.className = "staff__grid";
    const maxX = gates.reduce((m, g) => Math.max(m, g.x), -1) + 1;
    grid.style.width = `${SRC_W + Math.max(2, maxX) * GATE_W}px`;
    grid.style.height = `${Math.max(1, nmode) * ROW_H}px`;

    /* lanes (one per mode) */
    for (const r of rows) {
      const row = document.createElement("div");
      row.className = "staff__row";
      row.dataset.mode = String(r.mode);

      const src = document.createElement("div");
      const armed = placing && r.mode === placing.modeA;
      src.className = `staff__source${r.srcFirst ? "" : " staff__source--cont"}${armed ? " staff__source--arm" : ""}`;
      if (r.srcFirst) {
        src.textContent = `${OPS[r.srcOp].label}${r.srcOp === "tmsv" ? `(r=${r.srcParams.r ?? 0.6})` : ""}${r.srcOp === "coherent" ? `(α=${r.srcParams.alpha ?? 1})` : ""}`;
        src.dataset.srcId = r.srcId;
        src.addEventListener("click", () => {
          const n = api.getState().nodes.find((x) => x.id === r.srcId);
          if (n) openCard(n);
        });
      }
      row.appendChild(src);

      const lane = document.createElement("div");
      lane.className = "staff__lane";
      lane.dataset.mode = String(r.mode);
      if (armed) lane.classList.add("staff__lane--arm");
      row.appendChild(lane);
      grid.appendChild(row);
    }

    /* gate blocks (absolute over lanes) */
    const gatesEl = document.createElement("div");
    gatesEl.className = "staff__gates";
    for (const g of gates) {
      const el = document.createElement("div");
      el.className = `gate gate--${g.two ? "two" : "single"}`;
      el.dataset.id = g.node.id;
      el.style.left = `${SRC_W + g.x * GATE_W}px`;
      el.style.top = `${g.top * ROW_H}px`;
      if (g.two) el.style.height = `${g.span * ROW_H}px`;
      const title = document.createElement("span");
      title.className = "gate__title";
      title.textContent = OPS[g.node.op].label;
      const del = document.createElement("button");
      del.type = "button";
      del.className = "gate__del";
      del.textContent = "×";
      del.addEventListener("click", (e) => {
        e.stopPropagation();
        api.onDelete(g.node.id);
      });
      el.append(title, del);
      el.addEventListener("click", () => openCard(g.node));
      el.draggable = true;
      el.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData("text/plain", `move:${g.node.id}`);
        e.dataTransfer.effectAllowed = "move";
      });
      gatesEl.appendChild(el);
    }

    /* two-mode placing preview: translucent gate on the armed lane */
    if (placing) {
      const prev = document.createElement("div");
      prev.className = "gate gate--preview";
      prev.style.left = `${SRC_W + placing.x * GATE_W}px`;
      prev.style.top = `${placing.modeA * ROW_H}px`;
      prev.textContent = `${OPS[placing.op].label} ?`;
      gatesEl.appendChild(prev);
    }
    grid.appendChild(gatesEl);
    root.appendChild(grid);

    /* delegated events on the grid (gate blocks overlap lanes; closest(row)
       keeps drops/click working regardless of the actual target) */
    grid.addEventListener("dragover", (e) => e.preventDefault());
    grid.addEventListener("drop", (e) => {
      e.preventDefault();
      const rowEl = e.target.closest(".staff__row");
      if (!rowEl) return;
      const mode = Number(rowEl.dataset.mode);
      const x = (e.clientX - grid.getBoundingClientRect().left - SRC_W) / GATE_W;
      const data = e.dataTransfer.getData("text/plain") || "";
      if (data.startsWith("move:")) {
        api.onMove(data.slice(5), x);
        return;
      }
      const op = data;
      if (!Object.hasOwn(OPS, op) || OPS[op].palette === false) return;
      const meta = OPS[op];
      if (meta.kind === "source") {
        api.onStatus("源：请用托盘点击添加（源不参与拖放）", false);
        return;
      }
      if (meta.kind === "two") {
        placing = { op, modeA: mode, x };
        render();
        api.onStatus(`选择第二个模式（当前 mode ${mode}）`, false);
        return;
      }
      api.onPlace(op, mode, x);
    });
    grid.addEventListener("click", (e) => {
      if (!placing) return;
      if (e.target.closest(".gate")) return;
      const rowEl = e.target.closest(".staff__row");
      if (!rowEl) return; // blank outside lanes = cancel
      const mode = Number(rowEl.dataset.mode);
      const res = api.onCompletePlacing(placing, mode);
      if (res && res.ok === false) {
        api.onStatus(res.reason, false);
      } else if (res && res.ok) {
        placing = null;
        render();
      }
    });
  }

  root.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (placing) {
        placing = null;
        render();
        api.onStatus("已取消放置", true);
      }
      closeCard();
    }
  });
  root.tabIndex = -1;

  /* ── param card (click gate/source) ─────────────────── */
  let card = null;
  function closeCard() {
    if (card) { card.remove(); card = null; }
  }
  function openCard(node) {
    closeCard();
    const layout = staffLayout(api.getState());
    const meta = OPS[node.op];
    if (!meta) return;
    const g = layout.gates.find((x) => x.node.id === node.id);
    const row = g ? null : layout.rows.find((r) => r.srcId === node.id);
    const left = g ? SRC_W + g.x * GATE_W : 8;
    const top = g ? g.top * ROW_H : row ? row.mode * ROW_H : 8;
    card = document.createElement("div");
    card.className = "gate-card";
    card.style.left = `${Math.max(4, left - 74)}px`;
    card.style.top = `${Math.max(4, top - 62)}px`;
    card.addEventListener("click", (e) => e.stopPropagation());

    const head = document.createElement("div");
    head.className = "gate-card__head";
    const modeInfo = g
      ? (g.two ? `modes ${g.modeA}, ${g.modeB}` : `mode ${g.modeA}`)
      : (meta.kind === "source" ? `+${node.op === "vacuum" ? (node.params?.nmode ?? 1) : meta.modes} 模` : "");
    head.textContent = `${meta.label} · ${modeInfo}`;
    card.appendChild(head);

    const body = document.createElement("div");
    body.className = "gate-card__params";
    let any = false;
    for (const [k, d] of Object.entries(meta.params)) {
      if (d.advanced) continue; // nbar/nmode: JSON-only
      any = true;
      const wrap = document.createElement("label");
      wrap.className = "param";
      const lab = document.createElement("span");
      lab.className = "param__name mono";
      lab.textContent = k;
      const range = document.createElement("input");
      range.type = "range";
      range.min = d.min;
      range.max = d.max;
      range.step = d.step;
      range.value = node.params[k];
      const num = document.createElement("input");
      num.type = "number";
      num.className = "param__num mono";
      num.min = d.min;
      num.max = d.max;
      num.step = d.step;
      num.value = node.params[k];
      const push = (v) => {
        num.value = v;
        api.onParam(node.id, k, Number(v));
      };
      range.addEventListener("input", () => push(range.value));
      num.addEventListener("change", () => push(num.value));
      wrap.append(lab, range, num);
      body.appendChild(wrap);
    }
    if (!any) {
      const none = document.createElement("p");
      none.className = "gate-card__none";
      none.textContent = "无参数（该操作无旋钮；advanced 参数走 JSON）";
      body.appendChild(none);
    }
    card.appendChild(body);
    root.appendChild(card);

    if (Object.values(meta.params).some((d) => Array.isArray(d.sweep))) {
      api.onPickSweep(node.id);
    }
  }

  /* blank click closes the card */
  root.addEventListener("click", (e) => {
    if (e.target.closest(".gate-card") || e.target.closest(".gate") || e.target.closest(".staff__source")) return;
    closeCard();
  });

  return { render, isPlacing: () => placing !== null };
}
