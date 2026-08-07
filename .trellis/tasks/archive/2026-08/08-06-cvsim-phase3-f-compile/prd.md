# F-COMPILE 电路编译合并

## Goal

`GaussianCircuit` 升级为可编译执行：`circuit.compile() -> CompiledGaussian`，
`run()` 内部走同一编译路径（ADR-0002 决策 1）。逐门解释执行变为
"切段 → 段内合并 (S,d) → 执行"。

## Requirements

1. **断点规则**（ADR-0002 决策 2）：段边界 = 非幺正通道
   （loss / amplifier / phase_noise / gaussian_channel）、测量
   （measure_homodyne / measure_heterodyne）、含 ParamRef 的 op。
   段内 = 全部 affine 幺正 op（squeeze / displace / phase / fourier /
   beamsplitter / mach_zehnder / two_mode_squeeze / cz / cx / interferometer）。
2. **两层编译**（ADR-0002 决策 3）：`compile()` 结构编译（切段 + 收集
   `params`，含 ParamRef 源，O(n_ops)）；`run(**values)` 数值实例化
   （按值合并段为数值 (S,d)）+ 执行。每次 run 重新实例化，不缓存。
3. **API 面**（ADR-0002 决策 4）：`CompiledGaussian = { nmode, params:
   frozenset[str], run(**values) }`；不可变；不设 bind()；缺参
   ValueError；不暴露段布局。`circuit.run(**params)` 内部 =
   `compile().run(**params)`，行为不变（GaussianState | (state, results)）。
4. **段内 mode 映射**：段内 op 用电路原始坐标系 mode，数值实例化时按该段
   执行时的存活 mapping 转换（段内无测量，映射恒定）；删模后新段维度收缩。
5. 实现落位 `cvsim/gaussian/compile.py`（架构草图既有文件位）；
   公开导出走 `__init__.py` 白名单（ADR-0001 决策 4）。

## Acceptance Criteria

- [ ] 正确性 fixture ①：m=32 depth-100 随机 passive 电路，compiled vs
      naive 终态一致（atol=1e-9，vision exit metric）。
- [ ] 正确性 fixture ②：混合段电路（通道/测量/ParamRef 穿插），compiled
      vs naive 逐段中间态一致，含删模后段维度收缩、ParamRef 反馈路径。
- [ ] 正确性 fixture ③：参数化段（如 squeeze(r=$r$)）同结构不同 r 两次
      run 各自与 naive 一致。
- [ ] `circuit.run(**params)` 语义不变：无测量返回 GaussianState，有测量
      返回 (state, results)；缺参 ValueError；ParamRef 源未测 ValueError。
- [ ] 既有套件全绿（不回归 Phase 1/2 行为）。
- [ ] 性能基准（m=100 耗时/内存）**不在本任务**，归 benchmark-ci。

## Notes

- 架构决策见 docs/adr/0002-f-compile-compiler-architecture.md；
  术语（编译段/断点/结构编译/数值实例化/CompiledGaussian）见 CONTEXT.md。
- 与 serialize-ir 子任务边界：compile 不产 JSON，段布局不外露。
- 数值卫生：合并后 (S,d) 应用时保持 float64、symplecticity 默认校验
  （vision §7）；不引入新依赖。
