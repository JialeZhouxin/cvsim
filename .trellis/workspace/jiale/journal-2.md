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
