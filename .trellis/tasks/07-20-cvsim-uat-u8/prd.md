# UAT U8 · 扩展验收（①②③ 收口）

## Goal

一键 UAT 加 **U8**，冒烟覆盖本队列三切片：B 全复条件 Homodyne、Homodyne 采样 G/B、Fock 1 模 loss。更新 `USER_ACCEPTANCE.md` + `user_acceptance.py`。**无新物理。**

## Background

- ① `fcf53c4` B condition complex  
- ② `d76aa19` Homodyne sample  
- ③ `0016db2` Fock loss  
- 现 UAT：**U1–U5 + U7**，6/6；pytest **80**

## Decisions

| # | 选择 |
|---|------|
| D0 | 本任务 = ④ U8 only；无新算法 |
| D1 | **一个** `_u8()` 聚合冒烟（同 U7 风格） |
| D2 | 一键 demo：`U1–U5 + U7 + U8` → **7/7** |
| D3 | 数字复用 tests 量级；不引入第二套容差哲学 |
| D4 | 文档：能力矩阵 / 未做表 / pytest 计数同步 |

## Requirements

### U8 子项

| 子项 | 操作 | 期望 |
|------|------|------|
| B condition | `even_cat` → `homodyne_condition` +outcome | K=4；`∑w≈1`；+diag `|w|` > −diag |
| G sample | 真空 `N=2000` seed 固定 | `|mean|<0.08`；`|var−0.5|<0.08` |
| B sample | `from_gaussian` 同 seed ≡ G 单次 | 相对差 `<1e-12` |
| F loss | `\|1⟩` → `loss(T)` | `ρ₀₀≈1−T`，`ρ₁₁≈T`；`Tr≈1` |

### 文件

- `cvsim/demos/user_acceptance.py` + `_u8`
- `cvsim/USER_ACCEPTANCE.md`
- `cvsim/README.md` 若仍写 6/6
- quality 可选一行

## Acceptance Criteria

- [x] **AC-U1** 一键 7/7 PASS
- [x] **AC-U2** `USER_ACCEPTANCE` U8 + 未做表
- [x] **AC-U3** pytest 80
- [x] **AC-U4** 无新物理

## Out of Scope

- 新 gate / 新表示
- U6 并入一键（保持文档命令）
- Fock Wigner / 2 模 loss / sample_and_condition

## Notes

- 统计子项容差略松（seed 固定防 flaky）
- 打印：`U8 queue ①②③ smoke …`
