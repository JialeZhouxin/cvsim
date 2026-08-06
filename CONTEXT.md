# CV Photonic Notes

光学连续变量（CV）量子计算的教学笔记 + `cvsim` 最小三表示模拟器 + Gaussian Lab 图形工作台。同一物理以三种表示（Gaussian / Fock / Bosonic）呈现，教学与代码一一对应。

## Language

**cvsim**:
一个 numpy+scipy 的 CV 模拟器子包，与笔记中的物理一一对应。
_Avoid_: DQ, deepquantum, 模拟器库

**Gaussian 表示**:
用协方差矩阵 V 与均值向量 r̄（xxpp 约定）描述高斯态。
_Avoid_: 协方差形式, Wigner 表示

**Fock 表示**:
用截断 Fock 空间振幅/密度矩阵描述态，代价随模式数指数增长。
_Avoid_: 数态表示

**Bosonic 表示**:
多组分态：{(V_k, r̄_k, w_k)} 权重加权的 Gaussian 分量。
_Avoid_: 混合高斯表示

**circuit_v0**:
Gaussian Lab 的电路 IR schema 名（`schema: "circuit_v0"`），白名单 op 的图形/JSON 表示。
_Avoid_: 电路格式, schema v1

**nodes 顺序语义**:
`circuit_v0` 中 nodes 数组的顺序即执行顺序；edges 字段后端忽略（v0 无连线拓扑）。
_Avoid_: 图拓扑, 连线电路

**mode / modes**:
电路节点引用的运行时模号（单模 op 用 mode，双模 op 用 modes）。heterodyne 删模后后续节点模号自动重映射。
_Avoid_: 端口, 通道号

**heterodyne（外差测量）**:
v0 用均值路径（`heterodyne_mean` + condition），测后**删除**被测模；L3 换真抽样不破坏 schema。
_Avoid_: 外差采样

**homodyne（零差测量）**:
v0 不删模，与 `homodyne_condition` 语义对齐；测后态不变。
_Avoid_: 零差采样

**Wigner 热图视图（view）**:
后端对选定单模 `partial_trace` 后做 `wigner_grid`；`view` 字段含 `wigner_mode / lim / n`（n 上限 512）。
_Avoid_: 联合双模 Wigner, 3D Wigner

**meters**:
运行结果面板量：`purity`、`mean_photon`、`log_negativity`（+ 每模均值）。
_Avoid_: 读数, 指标

**log_negativity（对数负性）**:
TMSV 纠缠度量，T=1 时 = -log₂(e⁻²ʳ) = 2r/ln2；`modes_A` 指定二分 A 组，v0 硬编码 [0]（2 模唯一二分）。
_Avoid_: 负性, entanglement measure

**rbar / V**:
结果面板的均值向量与协方差矩阵（xxpp 块结构标注）。
_Avoid_: 协方差阵（不带 rbar）

**高斯态工厂**:
v0 源节点：vacuum / coherent / tmsv；tmsv 贡献 2 模，coherent 1 模。
_Avoid_: 态制备器, source node（英文保留 node）

**编译段（segment）**:
可合并的连续 affine 幺正 op 序列（squeeze/displace/phase/fourier/bs/mz/tms/cz/cx/interferometer），段内合并为单一 (S, d)。
_Avoid_: 层, 模块

**断点（break point）**:
编译段边界：非幺正通道、测量（删模）、含 ParamRef 的 op。断点后的常量 op 开启新段。
_Avoid_: barrier（中文语境）, 分隔符

**结构编译 / 数值实例化**:
compile() 只切段+收集参数名（结构编译，O(n)，不依赖数值）；run(**values) 按参数值把段内 ops 合并成数值 (S,d)（数值实例化，每次 run 重做，不缓存）。
_Avoid_: 预编译, 编译缓存

**CompiledGaussian**:
compile() 的不可变产物，公开面仅 {nmode, params, run}；多次 run 独立随机，不暴露段布局。
_Avoid_: 编译结果对象, bind 中间态

## Rules

- 术语以 vision-gaussian-lab-ui.md §4 白名单为准；新增托盘 op 必须先改 vision 再改 UI。
- 修改物理语义（如删模规则）必须先改 simulator vision / api-stability 文档，再改 Lab。
- 离线工作台：零外部依赖/CDN，前端系统字体栈；此约束属 ADR 级决策，不在此表内。
- 表示包互不 import；跨表示共享只放根级（conventions / symplectic / wigner），表示包根级 import 仅限 conventions + symplectic。见 docs/adr/0001。
- 分析概念（purity / entropy / fidelity）跨表示共享名字，实现按表示私有；不得跨包复用 analyse 实现。
- 公开 API = 各 `__init__.py` 的 `__all__` 白名单，白名单外视为私有。
