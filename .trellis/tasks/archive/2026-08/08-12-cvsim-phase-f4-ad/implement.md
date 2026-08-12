# Implement — Phase F4: Fock differentiable designer

> 2026-08-12 修正：ADR-0001 白名单约束（`test_architecture.py` AST 扫描，rep 包不得 import `cvsim.backend`）
> → backend 化不在 fock 包内做，新建**顶层** `cvsim/fock_ad.py`（镜像 `cvsim/ad.py` 模式）。fock 包零改动。

## 顺序检查清单

### Commit 1 — `cvsim/fock_ad.py` 可微链
- [ ] `squeeze_u(backend, N, r)`：numpy → `cvsim.fock.gates._squeeze_U`（真源）；jax → jnp 镜像 `expm(0.5r(a@a−ad@ad))`
- [ ] `bs_u(backend, N, theta, phi=0.0)`：numpy → fock BS 公式（真源）；jax → jnp 镜像（kron + expm）
- [ ] `kerr_diag(backend, N, chi)`：对角相位 `exp(1j χ n²)`，np/jnp 同式
- [ ] `cat_fidelity(backend, r, chi, *, alpha, T=1.0, cutoff=12)`：U→|0⟩→ρ→loss（`np.stack(_kraus_ops)` 常数 + einsum）→猫保真度
- [ ] `bs_overlap(backend, theta, *, cutoff=8)`：|1,0⟩→BS(θ)→|<0,1|ψ>|²（=sin²θ，BS 梯度测试链）
- [ ] 风格：`backend:` 首参、`_get_xp` 分发、与 fock/gates.py 公式交叉注释、诚实 docstring（mirror cvsim/ad.py）
- → verify: `py -3 -c "import cvsim.fock_ad; ..."` 冒烟；`pytest tests/test_architecture.py -q` 绿

### Commit 2 — `tests/test_fock_ad_f4.py`
- [ ] backend 参数化恒等：`cat_fidelity`/`bs_overlap` numpy vs jax 逐元素相等（conftest `backend` fixture）
- [ ] 梯度 vs fd ×3：squeeze r / BS θ / Kerr χ（`skipif(not be.HAS_JAX)`，h=1e-6，atol 1e-6 — Gaussian 同款 bar）
- [ ] jax 未装时全 skip、numpy 路径仍绿
- → verify: `py -3 -m pytest tests/test_fock_ad_f4.py -q` 全过；`pytest -k fock` 193+新 全绿

### Commit 3 — notebook
- [ ] `tutorials/_build_07.py` + `tutorials/07_fock_ad_designer.ipynb`（5 节：设定/网格扫描/jax.grad vs fd/梯度上升+η 生存曲线/结论；mirror `_build_05.py` 生成模式）
- [ ] 纯公共 API：只 import `cvsim.fock_ad` + `cvsim.fock`（教学约束：教程禁用 dq/DeepQuantum）
- → verify: `py -3 tutorials/_build_07.py` 生成成功；nbconvert execute Run-All 无错

### 收尾
- [ ] OCR review 3 个 commit（workflow Phase 3.4 强制）
- [ ] spec 更新（`.trellis/spec/backend/backend-interface.md`：Fock 侧镜像模式一条 — 顶层 `fock_ad.py` 落点）
- [ ] commit 顺序：`feat(fock): F4 可微链 fock_ad.py` → `test(fock): F4 梯度/恒等测试` → `docs: F4 notebook 07`
- [ ] `task.py finish` + `task.py archive`

## 验证命令

```bash
py -3 -m pytest tests/test_architecture.py -q       # ADR-0001 白名单（新模块无违规）
py -3 -m pytest tests/test_fock_ad_f4.py -q         # 新测试
py -3 -m pytest tests/ -k fock -q                   # 回归 193 + 新增
py -3 -m pytest tests/test_public_api.py -q         # 冻结面（零改动）
py -3 tutorials/_build_07.py                        # notebook 生成
```

## 风险文件 / 回滚点

- `cvsim/fock_ad.py` — 新文件，无回滚负担；唯一风险是 jnp 镜像公式漂移（恒等测试守护）
- `cvsim/fock/*` — 零改动（ADR 约束）
- commit 1/2/3 各自独立可回退

## follow-up（start 前）

- [ ] PRD/design/implement 三件齐 + 用户已批准
- [ ] implement.jsonl / check.jsonl 已放真实 spec 条目（见 jsonl）
