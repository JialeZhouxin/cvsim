# Implement · 三表示光量子模拟器

## Preconditions

- [x] 用户审查通过 `prd.md` + `design.md` + 本文件
- [x] `task.py start`（status → in_progress）
- [x] 开工前跑 `trellis-before-dev`（spec 多为 placeholder；以 design/prd 为准）

## Ordered checklist

### Phase 0 · 工程骨架

1. [x] `uv venv` + 安装 `numpy` `scipy`
2. [x] 建 `cvsim/` 包骨架与 `conventions.py`
3. [x] 三 demo 可跑

### Phase 1 · M1 Gaussian

1. [x] `GaussianState` + squeeze + det/⟨n⟩
2. [x] `python -m cvsim.demos.m1_gaussian_squeeze` — AC1.1–1.3 绿

### Phase 2 · M2 Fock

1. [x] `FockState` + ladder/`expm` squeeze + mean_photon/norm
2. [x] `python -m cvsim.demos.m2_fock_cutoff_scan` — AC2.1–2.3 绿
   - 截断酉保范数；AC2.3 用高 cutoff 演化再投影低 N 暴露亏损

### Phase 3 · M3 Bosonic

1. [x] 4 组件 even/odd cat + ∑w=1
2. [x] `python -m cvsim.demos.m3_cat_weights` — AC3.1–3.2 绿
3. [ ] AC3.3 Wigner 可选，未做

### Phase 4 · 收尾

1. [x] `cvsim/README.md`
2. [ ] 用户确认后 check / finish-work
3. [ ] 约定回写 `.trellis/spec`（可选）

## Validation commands

```bash
uv venv
uv pip install numpy scipy
# Windows: .venv\Scripts\activate 后，或直接：
.venv\Scripts\python.exe -m cvsim.demos.m1_gaussian_squeeze
.venv\Scripts\python.exe -m cvsim.demos.m2_fock_cutoff_scan
.venv\Scripts\python.exe -m cvsim.demos.m3_cat_weights
```

## Risky points

| 风险 | 缓解 |
|------|------|
| 正交序写反 | 测 \(V=½\mathrm{diag}(e^{\pm2r})\) |
| Fock 截断伪影 | 投影法验 AC2.3；⟨n⟩ 扫 cutoff |
| cat 权重 | ∑w=1 + 对角/交叉结构 assert |
| 过早 Circuit DSL | 未做 |

## Rollback

- 丢弃 `cvsim/` + `.venv`；笔记未改
