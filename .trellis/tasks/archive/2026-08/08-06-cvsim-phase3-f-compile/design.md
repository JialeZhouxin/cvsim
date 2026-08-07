# F-COMPILE 设计

架构决策见 docs/adr/0002。本文件记录实现级设计。

## 编译产物

`CompiledGaussian`（不可变）：`nmode`、`params`（可绑定参数名并集）、
`_segments`（段列表）。`run(*, rng=None, **values)` = 逐段执行。

## 段模型

`_compile_segments(ops) -> (segments, params)` 静态切段：

- **静态模拟 mapping**：测量删模数量确定（每次删 1 模），mapping 演化
  不依赖随机结果 → 结构编译时把每个 op 的 mode 预转为**物理坐标**，
  并记录每段执行时的 nmode。执行器不再维护 mapping 状态。
- 段类型两种：
  - `('merged', nmode, ops)` — 常量 affine 幺正段（无 refs），可合并
  - `('op', op)` — 单个断点 op：channel / measure / 含 refs 的 op，
    逐 op 执行
- 断点规则（ADR-0002 决策 2）：channel（loss/amplifier/phase_noise/
  gaussian_channel）、measure（homodyne/heterodyne）、含 ParamRef 的 op。
  断点后常量 op 开启新 merged 段。

## 数值实例化（merged 段）

因子表（复用 `cvsim.symplectic` 生成器，与 `gates.py` 同一数学源）：

| op | 因子 |
|----|------|
| squeeze | S = R(φ)S(r)R(−φ)（φ≠0 时），d=0 |
| displace | S=I, d=d_displace(alpha) |
| phase / fourier | S_phase(θ) |
| beamsplitter | S_beamsplitter |
| mach_zehnder | S_mach_zehnder |
| two_mode_squeeze | S_two_mode_squeeze |
| cz / cx | S_CZ / S_CX |
| interferometer | S_from_unitary(U) |

链式合并（op1 先作用）：`S ← Sᵢ@S; d ← Sᵢ@d + dᵢ`（float64，不校验
symplecticity——生成器可信，与 gates.py validate=False 一致）。
执行：`apply_symplectic(st, S, d, validate=False)` 一次乘法。

## 执行器（op 段）

从 `circuit.run()` 迁移，行为逐条对齐：

- measure_homodyne：采样+condition+remove_mode，结果入 `results`
- measure_heterodyne：采样+condition（内部删模），结果入 `results`
- gaussian_channel：`apply_gaussian_channel`，保留 X 维度 vs 当前
  nmode 的 ValueError 检查
- 其余：resolve pnames（查 values，缺→ValueError）+ refs（查 results，
  源未测→ValueError）→ `_apply` dispatch

## 公开面

- `GaussianCircuit.compile() -> CompiledGaussian`：无参，结构编译
- `GaussianCircuit.run(**params)`：改为 `self.compile().run(rng=rng, **params)`
- 内部函数（`_compile_segments`、`_instantiate`）为模块级私有，
  不进 `__init__.py` 白名单；测试可直接 import（fixture ② 逐段驱动）。

## 验证

- naive 对照 = 测试内手写逐 op 执行（gates 函数 + 测量函数 + channels
  apply + refs resolve + mapping 模拟），与编译路径独立实现。
- fixtures：① m=32 depth-100 随机 passive（atol=1e-9）；② 混合段逐段
  中间态一致；③ 参数化段同结构两次 run。
- 既有 `test_gaussian_circuit.py` 全绿 = run() 行为不变回归。
