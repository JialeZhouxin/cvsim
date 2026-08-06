# Design: undo/redo 撤销栈 + fourier 托盘缺口

## 1. undo/redo（主任务）

### 1.1 核心洞察：state 全程 immutable

`editor.js` 所有 mutation 都生成新对象（`{ ...state, nodes: ... }`、`nodes.map(...)`），**旧 state 引用永不被修改** → 历史栈只需存 `state` 引用，零拷贝、O(1)。

### 1.2 位置

全部在 `editor.js`（state 唯一拥有者）。`staff.js` 只读 state，不动。

### 1.3 栈设计

```js
const HISTORY_MAX = 50;
let history = [];   // 旧 state 引用栈（undo 可回退）
let redoStack = []; // redo 栈
```

- `pushHistory()`：`history.push(state)`，超限 `shift()`，清空 `redoStack`
- `undo()`：`history` 空 → 忽略；否则 `redoStack.push(state); state = history.pop(); render();`
- `redo()`：`redoStack` 空 → 忽略；否则 `history.push(state); state = redoStack.pop(); render();`
- render() 自动 emit → 电路刷新 + 后端运行，无需额外逻辑

### 1.4 各路径归属

| 路径 | push? | 说明 |
|------|-------|------|
| onPlace / onCompletePlacing / onMove / onDelete | ✅ | 拖放/删除 |
| palette click (addNode) | ✅ | |
| reset | ✅ | undo 可回退到重置前 |
| setState (载入 JSON) | ✅ | undo 可回到载入前 |
| onParam | ✅ | 拖动滑块每步一条；不做 coalesce（上限 50 兜底，ponytail: 加 coalesce 当 slider 拖动量大时） |
| setView (wigner_mode 选择) | ❌ | 显示设置，非电路编辑 |
| JSON textarea 直接编辑 | 清空双栈 | JSON 是编辑源；rebuild 成功后 `history=[]; redoStack=[]`（避免与图形操作历史语义混乱） |

### 1.5 触发

- 快捷键：`document` keydown — `Ctrl+Z` = undo，`Ctrl+Shift+Z` / `Ctrl+Y` = redo
- **排除**：`e.target.closest("input, textarea, select")` → 表单控件内交给浏览器原生（JSON 编辑/seed 输入不冲突）
- UI 按钮：seq panel head 加 `撤销` / `重做`（btn--ghost），render 时按栈空/非空置灰
- 注意 staff root 已有 Escape 处理（tabIndex=-1），undo 挂 document 层不受焦点影响

### 1.6 交互约束

- 撤销到空栈：静默忽略，不改状态栏（或提示"没有可撤销操作"，不强制）
- 载入新 JSON（setState）后旧历史仍有效（可 undo 回载入前）—— 符合预期
- 与 frozen-graph 策略兼容：非法操作不改 state 也不 push

## 2. fourier 缺口

**根因**：`ops.js` OPS 无 fourier 定义 → 托盘无、旧 JSON 也报"未知 op"。后端 `ir.py` L20/42/248 完整支持，vision §4.2 ✅ 列明确包含。

**修复**：`ops.js` OPS 加

```js
fourier: { label: "傅里叶", kind: "single", params: {} },
```

同步更新 `tests/editor.test.mjs` EXPECTED_OPS（+fourier，13→14）。后端零改动。

## 3. 主剧本复验

vision §5 剧本 1–6+8 手工过一遍（lab 起服务后浏览器/脚本验证）：
1. 拖 TMSV 设 r → 2. 两臂 loss → 3. Wigner 热态圆斑、r 增大变胖 → 4. BS 后读 Wigner/log_neg → 5. 拧参数刷新、E_N ≈ freeze 值 → 6. heterodyne 删模 → 7. Measure once → 8. Save/Load 拓扑一致
- 结果记入任务目录；TMSV 已出托盘（palette:false），剧本 1 改为：vacuum×2 + two_mode_squeeze 门 构建纠缠，或 JSON 载入 tmsv —— 按当前 UI 实际语义复验

## 4. 验证

1. `node --test tests/editor.test.mjs`（含新 undo/fourier 断言）
2. `node tests/lab_staff_probe.mjs`、`node tests/lab_scan_probe.mjs`
3. pytest 相关套件
4. 起 server 手工复验主剧本
