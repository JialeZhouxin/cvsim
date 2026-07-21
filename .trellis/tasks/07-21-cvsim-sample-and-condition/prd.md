# G3 · sample_and_condition

## Parent

`07-21-cvsim-gap-fill` 包 A · P0

## Goal

G/B 薄封装：`homodyne_sample_and_condition` = sample + condition。无新物理。

## Depends

无。

## Decisions

| # | 选择 |
|---|------|
| D1 | **薄 API**（非仅 demo） |

## Acceptance

- [ ] G 真空：outcome 后测向 var→0，⟨x⟩→outcome
- [ ] B from_gaussian 同路径
- [ ] tests 绿

## Out

新似然；改 sample 池规则
