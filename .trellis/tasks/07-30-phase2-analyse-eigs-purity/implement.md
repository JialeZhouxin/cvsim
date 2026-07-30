# Implement: F-ANALYSE-1

## 前置已完成
- [x] brainstorm 收敛（Q1–Q4）
- [x] PRD 收敛 pass
- [x] design 算法锁定 + 数值预演（Williamson Cholesky 路径 + slogdet 全 case 过）

## 执行步骤
1. **读现有 `analyse.py` + `__init__.py`**，确认插入点与导出列表。
2. **实现 `_as_cov` helper + `symplectic_eigenvalues` + `purity`** 于 `analyse.py`。
3. **导出** 更新 `cvsim/gaussian/__init__.py`。
4. **写 `tests/test_analyse.py`**，覆盖 design §测试对账点全部 case。
5. **跑 pytest**：`uv run pytest tests/test_analyse.py -q` 再全量 `pytest -q`。
6. **docstring 复核**：含愿景数学 + cite。

## 验证命令
```bash
.venv/Scripts/python.exe -m pytest tests/test_analyse.py -q
.venv/Scripts/python.exe -m pytest -q
```

## 风险/回滚
- R1: chol 在纯态 fail → jitter 路径；若仍 fail 查 V 是否真 PD。
- R2: thermal product 对账错 → 检查 `[::2]` 取法。
- R3: 导出漏 → `__init__.py` 与 `__all__` 双查。

## 实施后检查
- [ ] implement.jsonl / check.jsonl 真条目（非 _example）
- [ ] 用户验收或明示 go
