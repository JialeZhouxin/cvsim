# F3 — FockCircuit + compile + 稀疏（vision §F3 / ADR-0004 §1）

前置：F2（FOCK_PUBLIC 冻结，863 绿）。共享核 `cvsim/circuit_common`（ADR-0004）已就位。

## 切片

1. **f3-circuit**：`cvsim/fock/circuit.py` — FockCircuit builder（镜像高斯 DSL）：
   squeeze/displace/phase/beamsplitter/two_mode_squeeze/cz/cx/mach_zehnder/kerr/
   interferometer/apply_unitary + loss/amplifier/phase_noise/apply_kraus +
   `measure_pnr(mode, name)`（条件化，不移除模）/measure_homodyne/measure_heterodyne；
   per-mode cutoffs（`cutoff: int | list[int]`）；`compile()/run()` 同构单路径；
   **merged 段 = Kronecker 逐 op 应用**（tensordot 于模态轴，不物化 N^{2m} 全空间 U；
   段语义保留：参数绑定一次、测量断段）。
2. **f3-ir**：`to_ir()/from_ir()` 复用 circuit_v1（ADR-0003 单 schema）：`gaussian/ir.py`
   OP_META 扩展 Fock ops + from_ir 按电路类型分发（FockCircuit.from_ir）；
   naive vs compiled fixtures（m≤4）对照 exit criterion 1。
3. **f3-pnr-batch**：`pnr_sample_batch(circuit/state, size, rng)` 向量化 seeded
   （10³ shots 稳定 API，exit criterion 3）+ scale budget tests。
4. **f3-sparse**：稀疏振幅表示（`FockState(sparse=True)` 或稀疏子类，scipy.sparse，
   m≤10 光子数稀疏态 cat/GKP/单光子），与稠密对照（exit criterion 2）。

## Exit 条件（vision §F3）

1. Compiled vs naive 一致（fixtures m≤4）
2. Sparse vs dense 一致（cat/GKP/单光子，预算内）
3. 10³ PNR shots API 稳定；截断预算文档（vision §5）

## 非目标（F4+）

- backend=/JAX AD（F4）、桥转正（F5）、SF interop（F6）、GUI 评估（F3+ 开放）
- 双后端重构（ADR-0001 再评估留 F4）
