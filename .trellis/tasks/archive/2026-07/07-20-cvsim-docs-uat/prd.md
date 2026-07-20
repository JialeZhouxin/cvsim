# cvsim 文档与 UAT 收口

## Goal

把文档/UAT 对齐**当前代码能力**（G 全流程 · F 1–2 模 · B 矩+loss+gkp0）。**无新物理**。为 ② Wigner 铺路。

## Decisions

| # | 选择 |
|---|------|
| D1 | 改 `USER_ACCEPTANCE.md` + `user_acceptance.py` + `cvsim/README`（+ 根 README 一句） |
| D2 | 一键加 **U7** 扩展能力冒烟（loss / Fock BS / gkp0）；U1–U5 不动语义 |
| D3 | 「未做」列表更新；pytest 计数 **56** |

## Acceptance Criteria

- [x] UAT 文：能力边界与「未做」正确
- [x] 一键 U1–U5 + U7 全 PASS（6/6）
- [x] README 能力矩阵与包结构不旧
- [x] pytest 56 绿

## Out of Scope

- Wigner 实现（下一 task）
- 新算法
