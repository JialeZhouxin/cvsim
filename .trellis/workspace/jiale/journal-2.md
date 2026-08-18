# Journal - jiale (Part 2)

> Continuation from `journal-1.md` (archived at ~2000 lines)
> Started: 2026-08-18

---



## Session 57: Bosonic B3 测量精度——homodyne CDF 网格反演精确采样

**Date**: 2026-08-18
**Task**: Bosonic B3 测量精度——homodyne CDF 网格反演精确采样
**Branch**: `master`

### Summary

B3 完成：homodyne_sample 换 CDF 网格反演（删旧实峰池，复权重混合含干涉，返回 ndarray）；新增 homodyne_pdf 公共 API；condition 未动。15 项 B3 测试（cat vs Fock cutoff=30 atol=1e-7、Born 一致性解析核验、直方图、K=1 atol=1e-12）；1094 passed。trellis-check 审查全绿（warnings/filterwarnings 安全、导入边界、complex dtype、searchsorted clamp）；spec 更新（§4 教学切边界 + §6.1 B3 契约 + filterwarnings gotcha）。OCR 超时未跑成，记为残留。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `fb3cea7` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 58: Bosonic B4 调和对账——purity/pure_fidelity 闭式 + R1 分层套件

**Date**: 2026-08-18
**Task**: Bosonic B4 调和对账——purity/pure_fidelity 闭式 + R1 分层套件
**Branch**: `master`

### Summary

B4 完成：新增 cvsim/bosonic/analyse.py（purity 对角近似 + pure_fidelity 等 V 限制 Gram 矩阵）；公共面 39→41（+purity +pure_fidelity），phaseB4 marker。10 项 B4 测试（layer 1 退化 L1a-L1e atol 1e-7+ + layer 2 GKP 恒等式 L2a-L2e，GKP 无解析基准内部互验）。L2d/L2e 因等 V 限制改用 self-fidelity/purity。替代 deprecated gkp_logical_overlap。全套 1105 passed。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `d96fa3a` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 59: Bosonic B5 BosonicCircuit 电路 DSL——circuit_v1 第三消费者

**Date**: 2026-08-19
**Task**: Bosonic B5 BosonicCircuit 电路 DSL——circuit_v1 第三消费者
**Branch**: `master`

### Summary

B5 完成：BosonicCircuit 三件套（builder + compile + ir）镜像 Gaussian，复用 circuit_common 零修改。新增 BosonicState.remove_mode（partial trace，homodyne 手动删模）。公共面 41→45。16 项 B5 测试（compiled vs naive atol 1e-12、IR roundtrip lossless、测量+feedforward+删模、通道）。Lab 接入延后 B6（vision §6.2 硬边界：lab import bosonic 类比 Fock F7 解锁）。全套 1124 passed。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `125aae4` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete
