# Implement — Phase F5: Fock bridges + integration

## 顺序检查清单

### Commit 1 — 交叉核对套件
- [ ] `tests/test_fock_bridge_f5.py`：
  - PNR：`pnrd_probs` vs `|coherent_element|²` / `|squeezed_element|²` / `thermal_diag`（parametrize α/r/n̄，cutoff 按 tail<1e-9 选）
  - mean_photon 双表示：Gaussian `mean_photon`/闭式 vs Fock `mean_photon`（coherent/squeezed/thermal + 有损）
  - Threshold：Gaussian `p_click` vs Fock `1−pnrd_probs[0]`（三态）
  - 有损相干 η 扫掠：η ∈ {0.1,…,0.9}，Gaussian η|α|² / 1−e^{−η|α|²} vs Fock（cutoff 40，α=0.8，atol 1e-7）
  - 泄漏纪律：tail 断言先行（无静默比较）；截断不足必 fail 的负测试
- → verify: `py -3 -m pytest tests/test_fock_bridge_f5.py -q` 全过

### Commit 2 — 教程
- [ ] `tutorials/_build_08.py`（mirror _build_07.py 的 md/code/notebook 辅助）+ 生成 `tutorials/08_fock_bridge.ipynb`
  - 5 节：设定（双表示搭建）→ threshold p_click vs η 对账 → PNR 分布 → 截断生存曲线 → 结论（bridge 规则）
  - 只 import `cvsim.bridge` + `cvsim.fock` + `cvsim.gaussian`（禁 dq/DeepQuantum）
- → verify: `py -3 tutorials/_build_08.py` 生成成功 + Run-All 无错

### 收尾
- [ ] 全套件回归：`pytest -k fock`（218+新增）+ `test_public_api.py` + `test_architecture.py` 绿
- [ ] OCR review 任务 commit（Phase 3.4 前置，强制）
- [ ] spec 更新：bridge 跨表示规则如有新约定写回 `.trellis/spec/`（backend spec 无此域则记 vision-fock 状态节）
- [ ] commit 顺序：`test(fock): F5 交叉核对套件` → `docs: F5 notebook 08 双表示桥`
- [ ] `task.py finish` + `task.py archive`

## 验证命令

```bash
py -3 -m pytest tests/test_fock_bridge_f5.py -q   # 新套件
py -3 -m pytest tests/ -k fock -q                 # Fock 回归（218 + 新增）
py -3 -m pytest tests/test_public_api.py tests/test_architecture.py -q  # 冻结/架构零改动
py -3 tutorials/_build_08.py                      # notebook 生成
```

## 风险文件 / 回滚点

- 纯新增（1 测试文件 + 2 教程文件），无既有代码改动；单 commit 可整体回退
- squeezed 泄漏 vs atol 1e-7：参数选 tail 富余区（r≤0.4），泄漏断言先行

## follow-up（start 前）

- [ ] PRD/design/implement 三件齐 + 用户已批准
- [ ] implement.jsonl / check.jsonl 已放真实 spec 条目
