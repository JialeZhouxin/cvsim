# 票4：死绑定扫尾 — dom.runBtn / #state-summary / fock.js 双取

## 概述

删除审查确认的三处死绑定/残留（spec 问题 3）。纯删代码，无 red-green 可言——`/implement` 收尾时全量测试兜底 + 手工主剧本验证。[spec](./spec.md) 票 4/4。

## 变更

1. **editor.js:429 `dom.runBtn`**：`dom` 表中声明后全文件零引用 → 删该行。（app.js 的 `runBtn` 是自己的顶层 `$("run-btn")`，不受影响。）
2. **index.html:197 `#state-summary`**：`<summary>协方差 V <span id="state-summary" ...hidden></span></summary>` 无任何 JS 消费 → 删 span，保留 `<summary>协方差 V</summary>` 文本。（它本是 scan-summary 的镜像残留——scan 侧 #8 折叠摘要有消费者，state 侧从未接上。）
3. **fock.js 双取 `#fock-joint-svg`**：203 行裸 `document.querySelector("#fock-joint-svg")` 与 232 行 dom 表 `jointSvg` 键重复获取 → 删裸查询，203 处改用 dom 表条目（或把该条目提升到函数可及作用域，实现时取改动最小者）；获取点单一只剩 dom 表。

## 验收

- [ ] `grep -n "runBtn" cvsim/lab/static/editor.js` → 0 处
- [ ] `grep -rn "state-summary" cvsim/lab/static/` → 0 处
- [ ] `grep -n "fock-joint-svg" cvsim/lab/static/fock.js` → 恰 1 处（dom 表）
- [ ] pytest + node --test（显式列文件清单全量）全绿
- [ ] 手工主剧本：gaussian/fock/bosonic 三后端跑通——重点 fock 面板 joint 热图照常渲染（双取删除的回归面）、协方差 V 折叠摘要文本正常

**Blocks**: 无（与票1-3 相互独立，可任意顺序或并行）