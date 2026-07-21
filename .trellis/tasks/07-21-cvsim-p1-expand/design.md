# Design · P1 包 A（G7+G8）

## Graph

```text
父 07-21-cvsim-p1-expand
  ├─ G8 thermal-channel   (no dep)
  └─ G7 fock-s2           (no dep)
```

## G8

Touch:

- `cvsim/gaussian/channels.py` — `loss(..., nbar=0.0)`
- `cvsim/bosonic/channels.py` — 同签名
- `tests/test_thermal_loss.py`（新）
- 可选 README 一行

默认 nbar=0 保持旧行为；UAT U7/U8 不破。

## G7

Touch:

- `cvsim/fock/gates.py` — `two_mode_squeeze(state, r, mode1=0, mode2=1)`
- `cvsim/fock/__init__.py` export
- `tests/test_fock_s2.py`
- 对齐 `tests/test_b3_s2.py` 数字风格

仅 pure 2 模；`FockDensity` 2 模不在范围。

## Docs

各子任务改能力矩阵一句；或战役末一次改 `USER_ACCEPTANCE` 未做。

## Risk

| 风险 | 缓解 |
|------|------|
| nbar 改坏 pure loss | 默认 0 + 旧测全跑 |
| Fock S₂ 截断 | 小 r + 大 N；对 G 松容差 |
