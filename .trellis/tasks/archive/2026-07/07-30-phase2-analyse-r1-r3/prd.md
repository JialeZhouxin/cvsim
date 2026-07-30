# fix F-ANALYSE-1 review R1–R3

## Goal

按 `docs/review-07-30-phase2-analyse-eigs-purity.md` 修 3 个已复现缺陷，不推翻 Q4「不强制 validate」。

## Requirements

1. **R1 (P1)**：`purity` 开头 `V = 0.5 * (V + V.T)`，与 `symplectic_eigenvalues` / 愿景 §7 对齐。
2. **R3 (P2)**：`atol` 生效：`nu = np.maximum(nu, 0.5 - atol)`（不再硬编码 0.5）。
3. **R2 (P1)**：两函数 docstring 明确「不校验物理性；非物理可致 μ>1 / ν clip」；可选 `validate: bool = False`，`True` 时调 `is_physical` 拒绝。
4. 回归测试覆盖 R1/R2/R3 复现 case；全量 pytest 绿。

## Acceptance

- [ ] 反对称扰动 V：`purity` ≈ `∏ 1/(2ν)`（atol 内）
- [ ] `V=0.4I`：默认仍可算；`validate=True` raise
- [ ] 不同 `atol` 改变 clip 行为（可测）
- [ ] `pytest tests/test_analyse.py` + 全量绿

## Out of scope

- 不改默认强制 validate
- 不做 entropy_vn / 下游 F-ANALYSE
