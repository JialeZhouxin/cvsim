# ADR-0014: Lab 前端退役源节点，模数改为一等状态

- 日期: 2026-09-14
- 状态: 已接受
- 前置: ADR-0003（circuit_v1 IR）、ADR-0006 决策 2（`initial`/`cutoff` 扩展字段）、ADR-0011（退役 circuit_v0 前端）
- 任务: `.trellis/tasks/09-14-lab-frontend-retire-source-nodes/`

## 背景

Lab 前端（`cvsim/lab/static/`）自 v0 时代沿用「源节点」（source node）模型：
左侧谱（staff）每行由一个源节点提供，模数 = `sourceModes(state.nodes)`（各源
节点 `nmode` 之和）。ADR-0011 把导入路径切到 circuit_v1 后，**v1 IR 本身没有
源概念**（只有顶层 `nmode`），`stateFromV1` 因此硬造一个隐式源
（`vac0{nmode: payload.nmode}`）盖住全部谱行——一个只存在于前端的虚构对象。

由此产生三个真实缺陷：

1. **只显示 1 个模标签**：`staff.js` 只给「源的首行」画标签，其余是空白
   continuation 格。默认场景 2 模 → 左列只有 1 个「真空模」标签。
2. **标签内容撒谎**：标签只读 `OPS[srcOp].label`（`"真空模"`），**不读**
   `state.initial`——fock 后端下 mode 0 初始 3 光子照样写「真空模」。
3. **删源守卫恒拒**：`nSources <= 1` 的守卫使「删除」按钮在默认场景下永远
   无效（无法删到 1 模以下，但也无法删第 2 个模）。

## 决策

1. **`state.nmode` 是模数唯一事实源**（`defaultState()` 新增 `nmode: 1`；
   `stateFromV1` 返回 `nmode: payload.nmode`）。`sourceModes()` 及其 9 个调用
   点全部退役。
2. **`state.nodes` 永不含 source**：`stateFromV1` 不再注入隐式源；`OPS.vacuum`
   / `OPS.tmsv` / `OPS.coherent` 三个 op 删除；托盘「源」组退役（12 项 4 组
   → 11 项 3 组 门/通道/测量）。
3. **左列改为「模行」（mode row）**：`staffLayout(state).rows.length ===
   state.nmode`，每行一个模，标签 = `mode N · <初始态>`，读
   `state.initial[N]`（D1(b)）。初始态为空/零/非法 → 诚实显示「真空」，不撒谎。
4. **模标签是纯标签**（D2(i)）：不响应点击；初始态只在右侧「初始态」卡编辑。
   行内新增 `×` 删模按钮（`nmode === 1` 时 disabled）。
5. **删模语义**：`removeMode(nodes, mode)` = 删除该模上的全部门（单模命中 /
   双模任一命中）+ 索引 `> mode` 的模索引各减一。per-mode 数组
   （`initial` / `cutoffs`）按**索引删除**（新纯函数 `dropMode(arr, mode)`），
   不是截尾——`padTo`/`remapForBackend` 只做截尾/补位，直接复用会把被删模
   的值留在原索引（已实测 `remapForBackend("fock","fock",[3,5],1)` → `[3]`，
   值 5 丢失）。
6. **越界 view 字段**：删模后 `wigner_mode` 夹紧到 `nmode - 1`；`joint_modes`
   是**模索引**——命中被删模、或删后 `nmode < 2`（无对可指）→ 置 `null`（回退
   默认 `[0,1]`）；否则 > `mode` 的索引整体 −1（不重编号就会**指向另一个模**，
   静默错）。
7. **重申核心 IR 恒无源**：本决策是**纯前端**变更，`cvsim/lab/ir.py` 零改动，
   circuit_v1 字节输出不变。IR 里加源节点属被否方案（见下）。

## 被否方案

- **在 IR 加源节点**：1 源 1 模后，「N 个源」完全由 `nmode` 决定，映射满射且
  唯一，**没有信息可保**；源节点的「初始态」语义与既有 `initial` 扩展字段
  （ADR-0006 决策 2）重复；加源需走 `circuit_v2` 破坏性变更（ADR-0003 决策
  7），收益为零。若未来确需保留源的**分组身份**，正确落点是 `ui` 扩展字段
  （如 `ui.sources`），与 `ui.staff` 同一先例。
- **沿用 Q1=B 的 `nmode:N` → N 个 `vacuum{nmode:1}` 拆分**：被本轮彻底退役
  取代——只要源节点还在，上述三个缺陷就都得靠补丁绕（拆分 + 标签读
  `initial` + 修守卫），不如删掉源概念本身。

## 已知边界 / 白名单副作用

- **含源 op 的旧 JSON 会被拒**：`"op": "vacuum"` / `"tmsv"` / `"coherent"` 在
  `stateFromV1` 的 `Object.hasOwn(OPS, uiOp)` 白名单校验处失败。**这是故意
  行为**：源概念已退役，静默忽略会让用户以为导入成功。错误信息如实报
  op 名。
- **`stateFromV1` 不校验 `mode < payload.nmode`**：实测 `nmode:1, modes:[5]`
  被接受（既有行为，非本 ADR 引入）。越界门在 UI 上不可见但存在于 JSON。
  本 ADR 不做收紧，避免扩大范围；记入未来项。
- **gaussian 非真空初始态**：`initial` 对 gaussian 后端无定义（定义上恒真
  空），所以 gaussian 下左列标签恒为「真空」是**诚实**的。若未来要给
  gaussian 加非真空初态，属后端任务（后端没有对应 IR 字段）。
- **`ops_schema.js` pass 1 兜底**：schema 里的 `vacuum`/`tmsv`/`coherent` 条目
  被忽略（不再有 `V0_SOURCES` 镜像）。该分支仍在（服务 schema 内未知 op）。

## 影响

- 正面：模数与 IR 同源（`state.nmode`），前端不再维护虚构的源对象；左列标
  签诚实反映初始态；删模入口可用；托盘少一组无意义分类。
- 负面/边界：含 `"op":"vacuum"` 的历史 JSON 被拒导入（需手改 JSON）；被删模
  上的门级联消失（用户需知情——按钮 tooltip 与状态栏提示中文说明）。
- 契约：`toV1Json` 的 `nmode` 直读 `state.nmode`；IR 输出字节不变（AC4 用默
  认场景对拍锁定）。`ui.staff` 契约不变。
