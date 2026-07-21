# G1 · Fock 单模 Wigner

## Parent

`07-21-cvsim-gap-fill` 包 A · P0

## Goal

单模 Fock / `FockDensity` → \(W(x,p)\)；`wigner_grid` 挂接。ħ=1。

## Depends

无。

## Decisions

| # | 选择 |
|---|------|
| D1 | 支持 **FockState + FockDensity**（ρ 通用） |
| D2 | ħ=1 核：vac \(W(0,0)=1/\pi\)；\|1⟩ 原点负 |
| D3 | 仅 1 模；2 模 raise |

## Acceptance

- [ ] vac \(W(0,0)\approx1/\pi\)
- [ ] \|1⟩ \(W(0,0)<0\)
- [ ] pure 挤态逼近 G（中心区）
- [ ] tests 绿；无改 UAT（G4 做）

## Out

多模 Wigner；GUI
