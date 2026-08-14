# Bosonic B0+B1：基线冻结 + 能力完备

## Goal

B0 冻结测试面快照，B1 补齐 Bosonic 能力面至与 Gaussian 平级（vision §4 B1 exit 1–3），B1 出口冻结 `BOSONIC_PUBLIC`（设计 A11）。

## Requirements

- **B0**：现有教学 MVP 公共面测试快照（不改语义）；§2 约定冻结
- **B1 门**（对齐 Gaussian 命名集，K=1 atol）：`fourier` / `mach_zehnder` / `cz` / `cx` / `interferometer`（`symplectic.S_CZ/S_CX/S_mach_zehnder/S_from_unitary` 已有，薄封装）
- **B1 通道**：`amplifier`（G≥1, nbar=0 量子极限）、`phase_noise`（σ≥0，Option B 静态随机相位平均）—— 逐分量 X,Y 仿射（对齐 Gaussian channels.py）
- **B1 测量**（vision M1）：`heterodyne`（sample/condition/sample_and_condition）+ `threshold`（outcome-only，无态更新；p_click = 1 − Σ_k w_k ⟨0|ρ_k|0⟩，真空重叠用 `bridge.vacuum_probability`）
- **A4**：`measure.py` 新建，三测量同仓；homodyne 迁入（B1 先 re-export 保实现单一来源，B3 再重写）；observables 只留矩（mean_photon）+ weight_sum
- **A3**：`weight_sum` 归位 state.py（re-export 保兼容）；`is_hermitian` 属 B2（本任务不做）
- **工厂完成**：`coherent(alpha, nmode=1, mode=0)`（design A8 工厂白名单缺它）
- **A12**：`gkp_logical_overlap` docstring deprecated 标注（指向未来 pure_fidelity）
- **A11**：`BOSONIC_PUBLIC` 冻结清单写入 `tests/test_public_api.py`（镜像 GAUSSIAN/FOCK 块）

## Acceptance Criteria

1. **B1 exit 1**：门集与 Gaussian 命名集 1:1；`BosonicState.from_gaussian` 包装态经任意门 = Gaussian 门结果（V/r̄ atol 1e-10）
2. **B1 exit 2**：heterodyne（K=1 单模）条件化结果与 Gaussian 一致（退化态 nmode=0 等价）；threshold p_click 与 Gaussian `p_click` 一致（K=1, atol 1e-10）；混合态 p_click ∈ [0,1] 且虚部 ≈ 0
3. **B1 exit 3**：pytest 全绿（含新增 phaseB1 marker 测试）；无约定漂移（xxpp/ħ=1/√2 位移）
4. `test_public_api.py` 含 BOSONIC_PUBLIC 冻结块，`cvsim.bosonic.__all__` 精确匹配
5. homodyne 教学切 API（mean/var/sample/condition/sample_and_condition）经 `measure.py` re-export 后 import 路径不变
6. `gkp_logical_overlap` deprecated 标注落 docstring

## Out of Scope

- B2 组件工程（merge/truncate/leakage/is_hermitian）—— 下一任务
- B3 homodyne 精确采样 —— 下一任务
- heterodyne batch（`heterodyne_sample_batch`）—— 无场景，YAGNI
- B5 电路/IR、B6 GUI、B7 桥

## Notes

- 设计约束来源：`docs/vision-bosonic-simulator.md`（B1 exit）+ `docs/adr/0005` + 任务 `08-14-bosonic-architecture/design.md`（A2/A3/A4/A11/A12）
- heterodyne 混合态数学：逐分量 Gaussian 条件化（gaussian/observables.py 同公式）+ Husimi 边缘密度重加权 `w_k ∝ w_k·N(z; r̄_k, Σ_k)`，K=1 退化为纯 Gaussian 路径
