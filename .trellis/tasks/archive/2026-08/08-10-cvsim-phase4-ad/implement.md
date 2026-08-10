# Implement — Phase 4: Differentiable designer (F-AD) 执行计划

## 执行顺序（严格串行，每步 commit）

| # | Child | 产出 | 验证（每步） |
|---|-------|------|-------------|
| 1 | `phase4-ad-protocol` | `cvsim/backend.py`（`_get_xp`/`require_jax`/`_set`/`_block`/`_allclose`）+ `tests/test_backend.py` + pyproject `[jax]` extra + conftest `backends` fixture | pytest 新测试绿；592 回归绿 |
| 2 | `phase4-ad-gates-basic` | symplectic.py: `d_displace`/`S_squeeze`/`S_phase`/`S_beamsplitter`/`S_two_mode_squeeze` 加 backend + `tests/test_ad_gates_basic.py` | np 路径回归绿；jax 路径与 np 一致；**梯度 vs FD** |
| 3 | `phase4-ad-gates-advanced` | symplectic.py: `S_CZ`/`S_CX`/`U_beamsplitter`/`embed_U_2mode`/`S_from_unitary`/`S_mach_zehnder` + `tests/test_ad_gates_advanced.py` | 同上（不含梯度，含 jax 数值一致） |
| 4 | `phase4-ad-validate` | symplectic.py: `is_symplectic`/`validate_symplectic`/`is_unitary`/`validate_unitary` + `tests/test_ad_validate.py` | 参数化判定一致 |
| 5 | `phase4-ad-decompose` | symplectic.py: 3 个 decompose 函数加 backend 参数（jax→NotImplementedError）+ `tests/test_ad_decompose.py` | numpy 回归绿；jax raise 断言 |
| 6 | `phase4-ad-objective-notebook` | `cvsim/gaussian/ad.py`（apply + 可微 log_neg）+ `tests/test_ad_objective.py` + `tutorials/05_ad_designer.ipynb` | 梯度 vs FD；优化收敛到解析 r*(η)；notebook Run-All |

## 每步内部流程（trellis 标准）

1. `task.py start <child>` → status in_progress
2. 写测试（red）→ 跑 pytest 确认失败
3. 实现（green）→ 跑 pytest + 全量 592 回归
4. `trellis-check` 质量检查（spec 合规 / lint / 全量测试）
5. commit（feat/fix 前缀，中文描述）
6. OCR review（每任务必做，记忆里的既定纪律）
7. `task.py archive <child>` + `add_session.py`

## 验证命令

```bash
py -3 -m pytest tests -q                          # 全量（含 jax 用例需已装 jax）
py -3 -m pytest tests/test_ad_*.py -q             # 新测试
py -3 -m pytest tests -q -k "not ad"              # numpy 回归（无 jax 时等价全量）
pip install -e ".[jax]"                           # 启用 jax 路径（Windows CPU 即可）
```

## 风险点

- **np/jnp 差异**：`_block` 的 jnp 实现（嵌套 concatenate 的 shape 对账）最易错 → child 1 必须有等价性单测。
- **x64 未启用**：float32 下 atol=1e-8 全挂 → `_get_xp` 首次调用即配置，child 1 测试显式断言。
- **回归漂移**：symplectic.py 重写可能手滑改变 numpy 路径 → 每 child 硬编码已知值回归断言。
- **JAX 装不装**：本机装 `[jax]` 全量验证；CI 无 jax 时 skip 用例保绿。

## 收口（parent）

- 全 6 child 归档后：vision-gaussian-simulator.md 更新（F-AD 完成、gap 表、版本 0.3.0）、`CONTEXT.md` 术语（backend 协议、x64、_set/_block）、spec backend/ 更新（symplectic.py backend 化约定）、parent 归档。
- exit criteria 核对：exit 1（梯度 vs FD，child 2+6 测试）✅；exit 2（backend 参数化共享测试，全部 child）✅；notebook（child 6）✅。
