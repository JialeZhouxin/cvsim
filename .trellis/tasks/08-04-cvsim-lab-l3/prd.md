# PRD — Gaussian Lab L3: Save/Load + Measure once（homodyne + heterodyne 真抽样）

> 上游: `docs/vision-gaussian-lab-ui.md` §4.4（测量白名单）/ §5（主剧本 7–8）/ §6.3（随机性契约）/ §8（`POST /sample`）/ §10（A5、A6）/ §11–12（L3 = F-LAB-IO + F-LAB-SHOT）
> Exit: **A5**（Save → reload → 拓扑与 meters 一致）+ **A6**（Measure once：显示 seed；同 seed 可复现）

## 1. 问题

L2 已有拖拽编辑器全通主剧本 1–6，但两个缺口：
1. **无持久化** — 电路只活在浏览器内存，刷新即丢；`circuit_v0` JSON 无法导出/导入（A5 未达）。
2. **无真抽样** — 测量节点走 mean path（`heterodyne_mean`），homodyne 甚至是占位（outcome=None、状态不变）。"看到一次真实测量结果与 seed"（主剧本 7）不可做（A6 未达）。

## 2. 范围

### 做
- **F-LAB-SHOT**: `POST /sample` — 显式 `seed`，`np.random.default_rng(seed)`；按节点顺序**真抽样全部测量节点**（homodyne `homodyne_sample_and_condition` 保留 mode；heterodyne `heterodyne_sample_and_condition` 移除 mode）；后测量基于前测量条件态；返回有序 `measured[]` + 条件态 + Wigner/meters
- **F-LAB-IO**: Save = 浏览器下载 `circuit_v0` JSON；Load = 文件选择上传 → 校验（前后端双校验）→ 重建编辑器 → 自动 `/run`
- **homodyne 节点落地**: 补 `phi` 参数（quadrature angle，默认 0）；mean path 用 `homodyne_mean` 记录 outcome；sample path 用 `homodyne_sample_and_condition`
- **条件态视图**: Measure once 后结果区切换为抽样条件态显示（outcomes + seed + 条件态 Wigner/meters）；改参数 / 重跑 `/run` / Load 后回到解析视图
- **A5/A6 测试**: 同 circuit + 同 seed → 同 outcomes（可复现）；Save→Load 往返一致；多测量按序条件链

### 不做（defer）
- ❌ 抽样结果写回电路 JSON / 保存实验记录文件（Q2 → 不写回；Save 只存电路）
- ❌ localStorage 持久化（Q5 → 文件下载/上传）
- ❌ undo（P1）、扫参 `E_N(r)`（L4）、amplifier/MZ 等新 op（需 amend vision §4）
- ❌ batch sampling / compile 优化（模拟器 Phase 3）
- ❌ 多测量节点 UI 选择"测哪个"（Q1 → 全测）
- ❌ 抽样分布统计（多 shot 直方图等）

## 3. 设计决策（brainstorm 锁定）

| # | 决策 | 值 |
|---|------|-----|
| D1 | 多测量语义 | 按节点顺序**全部测量**；后测量基于前测量条件态；返回有序 `measured[]` |
| D2 | 抽样不写回 | `/run` 保持纯函数（mean path、无 RNG）；Save 只保存电路；同电路+同 seed 必定复现 |
| D3 | 端点形态 | 独立 `POST /sample`；body 同 `/run` 加 `seed`；内部 `run_circuit(..., rng=default_rng(seed))` |
| D4 | 条件态视图 | Measure once 后结果区显示抽样条件态 + outcomes + seed；改参数/`/run`/Load → 回解析视图 |
| D5 | homodyne | 补 `phi` 参数（`[0, 2π]`，默认 0）；mean path 记 `homodyne_mean`；sample path `homodyne_sample_and_condition`（**不删模**，V 奇异，与模拟器一致）；schema 不 bump（additive 可选字段，L0 D2 已锁"不破坏 schema"） |
| D6 | heterodyne | sample path 换真抽样（`heterodyne_sample_and_condition`，**删模**）；outcome 记 `[re, im]` |
| D7 | Save/Load 形式 | 浏览器下载 `.json` + 文件选择上传；非法 JSON/schema → 报错且**不覆盖**当前电路 |
| D8 | seed | JSON 顶层 `seed` 字段（已存在，L0 预留）；UI 可改（数字输入），Measure once 显示本次 seed |
| D9 | 测试 | 后端：同 seed 复现、异 seed 可异、多测量链、homodyne 保留/heterodyne 删模、`/run` 无 RNG 稳定；前端：纯函数单测（seed 解析、payload 构造）；Save/Load 往返 |

## 4. 验收

1. **A6**: `POST /sample` 同 circuit + 同 seed → `measured[]` 逐项相同；异 seed → 不承诺相同
2. **A5**: Save 下载 JSON → 刷新页面 → Load 上传 → 节点顺序/参数/Wigner/meters 与保存前一致
3. 主剧本 7: 点 Measure once → 显示 outcomes + seed；homodyne 后 nmode 不变、heterodyne 后 nmode-1
4. 多测量链: 电路含 homodyne+heterodyne → 顺序条件执行，`measured` 顺序 = 节点顺序
5. `/run` 回归: 无 seed 时结果与 L2 完全一致（mean path 未变）；`/sample` 不影响 `/run`
6. homodyne `phi=π/2` 抽样分布方差 = `½e^{2r}`（squeeze 后）等物理断言
7. 非法 Load: 坏 JSON / 错 schema → 前端红条报错，当前电路不变
8. 全套 pytest + ruff + node --test 绿；无外部资源（离线守卫维持）
9. vision changelog 0.5.0 条目 + 本任务归档

## 5. 风险

- **homodyne 条件态 V 奇异**（σ→0 方向）→ `wigner_grid` 对奇异 V 的行为需验证（可能退化）；对策：测试先行，必要时 wigner 计算对奇异方向容错（先确认 wigner_gaussian 是否处理 det(V)→0）
- **heterodyne 删模后 mode 号重映射** → L0 IR 已有运行时 mode 重映射（顺序语义），sample path 复用同一 `_apply` 流程即一致
- **同 seed 复现** → `default_rng(seed)` 每次从头创建，保证 shot 序列一致；`/sample` 单 shot，无跨调用 RNG 状态
- **前端文件上传** → 无框架 vanilla JS `FileReader`；错误路径用现有红条状态机
- **mean path 与 sample path 漂移** → 共享 `_apply` 执行骨架，仅测量分支换函数；golden 测试锁两边行为
