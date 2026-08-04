# PRD — Gaussian Lab L2: 拖拽编辑器（序列流水线）

> 上游: `docs/vision-gaussian-lab-ui.md` §4（白名单）/ §5（主剧本）/ §11-12（L2 = F-LAB-EDITOR + F-LAB-METERS）
> Exit: **A2**（无手写 Python 完成主剧本 1–6）+ **A3**（T=1 TMSV: log_neg ≈ -log₂(e⁻²ʳ) tol 内）

## 1. 问题

L1 只有 JSON 文本编辑。主剧本（拖 TMSV → 拖 loss → 看 Wigner → 拖 BS → 拧参数 → 拖 heterodyne）在纯 JSON 下"可完成但不可教学"。L2 = 图形化拖拽编辑器，无手写 Python 搭出主剧本电路。

## 2. 范围

### 做
- **F-LAB-EDITOR**: 序列流水线编辑器（拖 op 入列表 = 追加尾部；参数面板编辑；上移/下移/删除；实时 JSON 双向映射）
- **F-LAB-METERS**（L2 部分）: 滑块参数编辑 + 100–150ms 防抖自动刷新
- JSON 编辑保留为**文本 ⇄ 图形双向同步映射**（改 JSON 实时重建图形，改图形实时更新 JSON）
- A3 数学验证：`log_negativity` T=1 时贴近 -log₂(e⁻²ʳ)

### 不做（defer）
- ❌ 真画布/端口连线（Q1 → b 序列流水线）；拖拽排序（Q9 → 上移/下移）
- ❌ `modes_A` bipartition 选择器（Q6 → 2 模唯一二分够用；3 模电路出现时再补，vision 注记）
- ❌ undo（P1）、Save/Load（L3）、Measure once（L3）、扫参（L4）
- ❌ 非白名单 op（MZ/CZ/interferometer/amp/phase_noise…）
- ❌ 托盘多余项：白名单 12 op 中只上主剧本必需 4 + 常用 4

## 3. 设计决策（grill 锁定）

| # | 决策 | 值 |
|---|------|-----|
| D1 | 编辑器形态 | **序列流水线**：托盘 → 拖 op 到列表（追加尾部）；nodes 顺序 = 执行顺序（对齐 L0 IR，零语义改动） |
| D2 | 托盘范围 | 8 op：`tmsv`/`loss`/`beamsplitter`/`heterodyne`（主剧本必需）+ `squeeze`/`coherent`/`phase`/`displace`（常用）。白名单其余（vacuum/fourier/two_mode_squeeze/homodyne）defer |
| D3 | 参数交互 | **滑块 + 数字输入双态**：r∈[-3,3] 步 0.01 · T∈(0,1] · θ∈[0,2π] · α∈[-5,5]；拖动防抖 120ms 自动刷新 |
| D4 | JSON 去留 | 保留，**双向同步**：图形编辑 → JSON 实时更新；JSON 编辑 → 图形重建（parse 失败 = 红条，图形冻结为上次合法态） |
| D5 | modes_A | 硬编码 `[0]` 保持（L1 现状）；prd 注记未来 3 模时加选择器 |
| D6 | 排序/删除 | 上移/下移/删除按钮；托盘拖入 = 追加 |
| D7 | 测试 | 编辑器 state→JSON 纯 JS 函数 + node 单测；后端不变（复用 /run）；主剧本手工验收（用户） |
| D8 | 视觉 | 延续 L1 Hallmark（Workbench/Cobalt）；左托盘 + 中序列 + 右结果（结果区复用 L1 组件） |

## 4. 验收

1. 主剧本 1–6 无手写 Python 走通（用户手工验收）
2. A3: T=1、r=0.6 TMSV → log_neg ≈ 1.731（= -log₂(e^(-1.2))），atol 1e-3（复用 L0 已有 API 断言 + 前端显示值）
3. 双向同步: 图形改 r → JSON 文本同步变；JSON 改 T → 图形参数面板同步变
4. 防抖: 滑块拖动连续变化 → 120ms 内仅 1 次 /run（可测：fetch 计数）
5. 全套 pytest 绿 + ruff + node 单测
6. 无外部资源（离线守卫测试维持）
7. vision changelog 0.4.0 条目

## 5. 风险

- 拖拽 HTML5 DnD 在 Windows Edge 可用性 → 降级方案：托盘项也可点击"+"追加
- JSON parse 失败冻结语义 → 双向映射用"合法态缓存"实现（不阻塞图形）
- 滑块高频 /run → 防抖 + 请求序号守卫（丢弃过期响应，防竞态）
