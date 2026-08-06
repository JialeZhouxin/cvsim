# ADR-0002: F-COMPILE 编译器架构

- 日期: 2026-08-06
- 状态: 已接受

## 背景

Phase 3 F-COMPILE 要把 `GaussianCircuit` 从逐 op 解释执行升级为可编译执行。
vision §5 只锁定了数学（affine 合并公式 S = S_n⋯S_1, d = d_n + S_n d_{n-1} + ⋯）、
合并边界三原则（非幺正通道 / 测量 / RNG 依赖 feedforward）与 exit metric
（m=32 depth-100 随机 passive 电路 atol=1e-9 且更快），并预留 `compile.py`
与 `circuit.compile() -> CompiledGaussian` 的轮廓。但架构未定：
编译产物形态、参数化 gate 如何进编译段、公开 API 面，均有多个可行方案。
grill-with-docs 审问 Q1–Q4 拍板如下。

## 决策

1. **编译模型 C：显式 compile() + run() 走同一路径**。
   `circuit.compile() -> CompiledGaussian` 是公开面；`circuit.run(**params)`
   内部等价于 `compile().run(**params)`。**不存在两套执行器**——
   "compiled vs naive identical" 由构造保证，不靠测试逐例证明。
2. **断点规则（精确化 vision 的"RNG 依赖 feedforward"）**。编译段边界：
   - 非幺正通道：`loss` / `amplifier` / `phase_noise` / `gaussian_channel`
   - 测量：`measure_homodyne` / `measure_heterodyne`（删模使后续段维度收缩）
   - **任何含 `ParamRef` 参数的 op**：其值依赖先前测量的随机结果，
     编译时未知，所在 op 单独构成动态段；之后的常量 op 开启新段（可编译）。
   段内保留全部 affine 幺正 op：`squeeze` / `displace` / `phase` / `fourier` /
   `beamsplitter` / `mach_zehnder` / `two_mode_squeeze` / `cz` / `cx` /
   `interferometer`。
3. **两层编译**。
   - 结构编译（`compile()`）：切段、收集**可绑定参数名**（pnames 的符号名并集，
     不含 ParamRef 源），不依赖任何参数数值，O(n_ops)。
   - 数值实例化（`run(**values)`）：按当前参数值把段内 affine ops
     合并为数值 (S, d)，再执行。每次 run 重新实例化，**不缓存**数值结果。
   参数化 / 变分电路因此获得与常量电路相同的编译收益；
   m=100 depth-100 一次实例化约 O(10⁶) flops，可忽略。
4. **API 面最小化**。`CompiledGaussian = { nmode, params: frozenset[str], run(**values) }`。
   不设 `bind()`（run 传参即绑定，缺参 raise ValueError，与 `Circuit.run`
   一致）；对象不可变（段列表快照，多次 run 独立随机）；
   不暴露段布局 / S / d（serialize 任务另定 JSON 形状）。

## 权衡

- **仅常量段编译 vs 两层编译**：常量版实现最简，但参数化电路零收益——
  而变分 / Lab sweep 恰是编译收益最大的场景。选两层。
- **前缀合并 vs 全电路分段**：vision 的 `compile_unitary_prefix` 只覆盖
  "测量前的一段"，覆盖不了"测量→再操作"的真实流程（ParamRef 反馈、
  feedforward 都在测量之后）。选全电路分段，前缀只是特例。
- **显式 compile() vs 仅 run() 自动**：仅自动版 API 最薄，但编译产物
  无法复用、无法被 serialize / Lab 消费，且"自动"会掩盖执行器双轨漂移。
- **bind() 中间态**：被否，YAGNI；run 传参即绑定，少一个状态。

## 后果

- F-COMPILE 正确性 fixtures 三种：① vision 标准（m=32 depth-100 随机
  passive，atol=1e-9）；② 混合段电路（通道/测量/ParamRef 穿插，compiled
  vs naive 逐段一致，含删模后段维度收缩）；③ 参数化段（同一结构不同 r
  两次 run 一致）。性能基准（m=100 耗时/内存）归 benchmark-ci 子任务。
- `run()` 缺参报错时机从"逐 op 执行时"提前到"数值实例化时"，行为仍为
  ValueError，不破坏 API。
- 与 serialize-ir 子任务边界：compile 不产 JSON，段布局不外露。
- 实现落位 `cvsim/gaussian/compile.py`（vision 架构草图已有该文件位）。
- 编译段内 op 的 mode 引用仍为电路原始坐标系；数值实例化时按该段
  执行时的存活 mapping 转换（段内无测量，段内映射恒定）。
