# Bosonic B1 — 实施计划

## 顺序（依赖优先）

1. `state.py`：`coherent` 工厂 + `weight_sum` 迁入 + `nmode` 空态返回 0
2. `gates.py`：5 新门薄封装
3. `channels.py`：amplifier / phase_noise
4. `observables.py` → `measure.py`：homodyne re-export + heterodyne + threshold（新文件）
5. `gkp.py`：deprecated 标注
6. `__init__.py`：BOSONIC_PUBLIC 冻结 `__all__`
7. 测试：test_b1_bosonic_channels.py / test_b1_bosonic_measures.py / test_public_api.py BOSONIC 块 / test_b1_bosonic_gates.py 扩展
8. `docs/api-stability.md` §2.2：cvsim.bosonic 升级"B1 冻结面"注记

## 验证命令

```powershell
.venv\Scripts\python.exe -m pytest tests/test_b1_bosonic_gates.py tests/test_b1_bosonic_channels.py tests/test_b1_bosonic_measures.py tests/test_public_api.py -q
.venv\Scripts\python.exe -m pytest -q          # 全套回归（Gaussian/Fock 零波及）
```

## 风险/回滚

- heterodyne 教学切（实对角池）必须 docstring 标注，与 B3 精确化边界划清
- threshold 真空重叠复分量虚部容差检查严格（>1e-8 抛错）
- 回滚点：每文件独立 commit；先代码后测试顺序提交，单文件可 revert

## 实施后检查（task.py start 之前）

- [ ] prd 验收 1–6 全过（K=1 atol、pytest 全绿、冻结块精确匹配、re-export 兼容、deprecated 标注）
- [ ] vision B1 exit 1–3 逐条核对
- [ ] `task.py start` → 实现 → `task.py archive`
