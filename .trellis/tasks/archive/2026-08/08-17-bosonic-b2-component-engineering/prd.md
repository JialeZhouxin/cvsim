# Bosonic B2：组件工程

## Goal

在 B1 已完成能力面的 `BosonicState` 上建立生产级组件工程纪律：组件合并、幅度截断、下溢处理、权重归一化、厄米性校验，以及显式的组件截断质量报告。为 B3 精确测量、B4 对账和后续电路执行提供稳定基础。

## Subtasks and execution order

四个子任务按以下顺序串行执行；它们共享 `component_eng.py` 和测试契约，不并行修改同一文件：

1. `08-17-bosonic-b2-invariants-report` — `LeakReport`、有限性校验、`normalize()`、`is_hermitian()`。
2. `08-17-bosonic-b2-merge` — 稳定贪心 `merge()` 与合并畸变报告。
3. `08-17-bosonic-b2-truncate` — `amp_cutoff`、泄漏阈值、警告/失败和空状态边界。
4. `08-17-bosonic-b2-integration` — 顶层导出、公共 API 冻结、`phaseB2`、文档与回归。

每个子任务完成后先通过其专项测试，再进入下一个子任务；最终由 B2.4 执行全套验证。

## Scope

- 新增 `cvsim/bosonic/component_eng.py`，保持纯函数风格，不引入张量引擎或新依赖。
- 合并近邻/等价 Gaussian 组件，并可量化合并造成的近似质量。
- 按 `amp_cutoff` 截断小权重组件；任何丢弃都必须可追踪。
- 处理权重下溢/数值噪声，不静默掩盖物理质量损失。
- 提供 `weight_sum` 归一化相关能力和 `is_hermitian` 共轭对闭合校验。
- 提供 `LeakReport`，显式报告丢弃权重质量与合并畸变估计。
- 将必要 API 接入 `cvsim.bosonic`，同步更新冻结公共面/文档/术语（若现有冻结策略要求）。

## Locked design decisions

### B2-1：组件合并判定

仅当两个组件的 `V` 与 `rbar` 分别在显式 `atol/rtol` 范围内接近时，才视为同一类组件并允许合并。`w` 不参与同类判定；合并时权重相加。`rbar` 比较保留复数语义，不强制取实。

### B2-2：合并代表值

**已确认：选项 A。** 合并后的 `V` 与 `rbar` 采用合并组中的第一个组件作为确定性代表值，权重为组内权重之和。这样不引入额外物理参数，也避免复权重相消时加权平均不稳定；近邻几何差异由 `LeakReport` 的合并畸变字段显式报告。

### B2-3：截断返回值

**已确认：选项 A。** `merge()` / `truncate()` 保持纯函数并返回 `(new_state, LeakReport)`；不修改输入，不用额外结果包装类。B2 阶段由调用方显式调用，不自动改变既有门、通道行为。

### B2-4：泄漏阈值纪律

**已确认：选项 A，镜像 Fock。** 默认 `warn_threshold=1e-6`、`fail_threshold=1e-3`：超过警告阈值发出 `RuntimeWarning`，超过硬失败阈值抛出 `ValueError`；`validate=True` 时超过警告阈值即抛出 `ValueError`。未知质量不得猜测为零，也不得静默吞掉。

### B2-5：截断后的归一化

**已确认：选项 A。** `truncate()` 不自动归一化，避免把截断造成的质量损失隐藏掉；截断后的 `weight_sum` 可以暂时不等于 `1`。需要归一化时由调用方显式调用 `normalize(state)`，并让归一化行为可测试、可追踪。

### B2-6：零权重和的归一化

**已确认：选项 A。** `normalize(state, atol=1e-12)` 计算 `s = weight_sum(state)`；若 `abs(s) <= atol` 则抛出 `ValueError`，否则每个权重变为 `w_k / s`。返回新状态，不修改输入；`V`、`rbar` 不变，也不负责修复厄米性。

### B2-7：下溢与数值噪声

**已确认：显式阈值、单一入口。** 不新增独立的“下溢修复”机制；统一由 `truncate(..., amp_cutoff=...)` 按 `abs(w)` 判断可丢弃组件。接近零的权重被移除时计入 `LeakReport`，不静默改写为实数或调用 `nan_to_num`。`amp_cutoff` 必须非负；`NaN/Inf` 权重直接抛出 `ValueError`，不得伪装成零。

### B2-8：厄米性校验

**已确认：只校验，不自动修复。** `is_hermitian(state, atol=..., rtol=...)` 检查每个组件是否存在对应的共轭组件：`V` 相同、`rbar` 为共轭、`w` 为共轭；实均值/实权重允许与自身配对。缺少配对或超出容差时返回 `False`，不修改输入、不强制取实、不自动补项。

### B2-9：组件工程调用方式

**已确认：显式调用、保持现有语义。** B2 只提供 `merge()`、`truncate()`、`normalize()`、`is_hermitian()` 等显式 API；不把组件合并、截断或归一化隐式塞入已有门、通道和测量函数，避免改变 B1 行为和掩盖组件质量成本。

### B2-10：LeakReport 字段

**已确认：最小不可变报告。** `LeakReport` 使用 `@dataclass(frozen=True)`，至少记录：

- `input_components`：输入组件数；
- `output_components`：输出组件数；
- `dropped_components`：截断/下溢丢弃的组件数；
- `dropped_weight_mass`：被丢弃权重的 `Σ|w|`，作为保守的质量预算，不作为归一化判据；
- `merge_groups`：发生合并的组数；
- `merge_distortion`：合并前后 `V`/`rbar` 的最大几何差异估计；
- `warning`：是否越过警告阈值。

报告只记录事实，不负责修复状态；`Σ|w|` 仅用于报告丢弃预算，仍不得替代 `Σw=1` 的归一化判据。

### B2-11：公共 API 暴露

**已确认：选项 A。** `LeakReport`、`merge()`、`truncate()`、`normalize()`、`is_hermitian()` 从 `cvsim.bosonic` 顶层导出；实现仍集中在 `component_eng.py`，并同步更新 `BOSONIC_PUBLIC` 冻结测试。

### B2-12：组件分组策略

**已确认：选项 A。** `merge()` 按输入顺序稳定贪心分组：从第一个未处理组件开始作为组代表，后续组件只与该代表比较；`V` 和 `rbar` 均满足 `allclose` 才加入；每组代表保持第一个组件，权重相加。避免链式接近导致的过度合并，结果可复现。

### B2-13：合并畸变定义

**已确认：选项 A。** `merge_distortion` 是每个合并组内、相对于第一个代表组件的 `V` 与 `rbar` 元素绝对差的最大值，再对所有组取最大值；无合并时为 `0.0`。该字段只记录事实，不额外触发警告或失败；是否允许合并由 `atol/rtol` 决定。

### B2-14：merge 的归一化前提

**已确认：选项 A。** `merge()` 不要求输入已归一化，只合并组件并保持权重总和不变；它既不自动归一化，也不因 `weight_sum != 1` 失败。归一化由调用方显式执行 `normalize()`。

### B2-15：截断边界

**已确认：选项 A。** `truncate()` 仅移除 `abs(w) < amp_cutoff` 的组件；恰好等于阈值的组件保留。`amp_cutoff=0` 不会因为边界比较误删组件。

### B2-16：全量截断

**已确认：空状态 + 报告，受阈值纪律约束。** 若 `truncate()` 移除所有组件且 `dropped_weight_mass <= fail_threshold`，返回 `BosonicState(components=[])` 与正常的 `LeakReport`；不自动补真空。若丢弃质量超过 `fail_threshold`，按 B2-4 抛出 `ValueError`；`validate=True` 时超过 `warn_threshold` 即抛出。后续需要物理态的操作自行通过现有 API 报告空状态错误。

### B2-17：normalize 返回值

**已确认：选项 A。** `normalize(state) -> BosonicState` 只返回新状态，不返回 `LeakReport`；仅改变权重，不改变组件数量、`V` 或 `rbar`。输入保持不变。

### B2-18：merge 默认容差

**已确认：选项 A。** `merge()` 默认使用 `atol=1e-10`、`rtol=1e-8`；调用方可以显式调整。该默认值偏保守，避免误合并物理上不同的近邻峰。

### B2-19：truncate 默认 amp_cutoff

**已确认：选项 A。** `truncate()` 默认使用 `amp_cutoff=1e-6`，与默认警告阈值一致；判定仍为严格的 `abs(w) < amp_cutoff`。调用方可显式传入更严格或更宽松的阈值。

### B2-20：组件工程顺序

**已确认：选项 A。** 不新增组合 API；调用方显式分两步，推荐先 `merge()` 后 `truncate()`，分别保存两个 `LeakReport`。调用方也可以显式选择相反顺序，库不隐式改变顺序。

## Non-goals

- 不做 B3 精确 homodyne CDF 采样与精确条件化.
- 不做 B4 完整跨表示对账套件。
- 不做双模生产级扩展、PNR 组件式路径、Kerr/任意非高斯门、AD、tensor network。
- 不重写 B1 已有门、通道、测量语义。

## Locked constraints

- 组件仍为 dataclass 列表：`(V, rbar, w)`。
- 权重归一化判据是 `Σ_k w_k = 1`；不得使用 `Σ|w_k|` 作为归一判据。
- 厄米性按共轭对闭合判断；复权重不可被强行取实。
- 默认阈值：组件质量 > `1e-6` 发出警告，> `1e-3` 硬拒绝；具体参数命名和异常类型须以现有代码/规范为准。
- 保持函数式：工程操作返回新状态，不就地修改输入。
- 不把 GKP 的理论近似伪装成精确结果；报告必须能区分丢弃质量与合并畸变。

## Acceptance criteria

1. `component_eng.py` 提供架构设计 A6 约定的最小组件工程 API，并有清晰 docstring/type hints。
2. 合并对等/近邻组件可保持权重和、厄米性，并在合并误差超过阈值时可观测。
3. `amp_cutoff` 能移除小权重组件并在 `LeakReport` 中记录被丢弃质量；零组件/全丢弃等边界行为有测试。
4. 下溢与接近零的数值噪声处理可重复、无静默物理损失；异常/警告行为有测试。
5. `weight_sum` 归一化与 `is_hermitian` 对实权重、复共轭对、破坏共轭闭合三类情形有测试。
6. 组件操作不改变输入状态；现有 B1 测试和全套回归保持通过。
7. 公共 API 冻结清单、`CONTEXT.md` 或 vision 文档仅在确有必要时最小更新，不扩散未请求的 API。

## Verification

```powershell
.venv\\Scripts\\python.exe -m pytest tests/test_bosonic_component_eng.py tests/test_public_api.py -q
.venv\\Scripts\\python.exe -m pytest -q
```
