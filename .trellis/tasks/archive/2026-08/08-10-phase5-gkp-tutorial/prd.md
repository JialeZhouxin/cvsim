# Phase 5 C3 — GKP feedforward 教程

## Goal

`tutorials/06_gkp_feedforward.ipynb`（中文教学）—— GKP 逻辑比特 + 位移错误检测（grill Q4 锁定）。Phase 5 exit 1 主体：CZ + measure + ParamRef 三要素 + compile().run(values) 闭环。

## Requirements

- `tutorials/_build_06.py` + `06_gkp_feedforward.ipynb`（6 节，风格对齐 05）：
  1. GKP 思想 + 强挤压 Gaussian 近似（诚实标注：非理想峰）
  2. 电路：GKP(ancilla 强挤压) + CZ(data, ancilla) + homodyne(ancilla, p)
  3. ParamRef 反馈修正（`c.displace(0, alpha=ParamRef('m_p', gain))`）
  4. compile().run(values) 数值闭环
  5. 位移误差扫描：ε 注入 → 读出线性响应 → 修正残差
  6. 小结 + 局限
- 教程自检断言（Run-All 可执行）
- `tests/test_gkp_tutorial.py`：关键数值回归（读出≈标定值、修正后方差下降）

## Acceptance Criteria

- [ ] AC1（exit 1）: CZ + measure + ParamRef 电路文档化 + Run-All 全过
- [ ] AC2: 检测→修正闭环断言成立（误差注入后修正效果显著）
- [ ] AC3: 全量 pytest 绿；commit + OCR
