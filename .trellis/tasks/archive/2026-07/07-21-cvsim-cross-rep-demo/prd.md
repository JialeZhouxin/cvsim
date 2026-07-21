# 跨表示同一物理 demo

## Goal

一个教学 demo `m4_cross_rep`：同一物理题打印多列数字，差在容差内。**无新物理 API**。

## Background

- 策略 B；笔记对齐 A 已归档 `4521b85`
- 用户选 **包 A = T1 + T4**

## Decisions

| # | 选择 |
|---|------|
| D0 | demo only；无新公式 |
| D1 | **T1 + T4** only |
| D2 | 文件：`cvsim/demos/m4_cross_rep.py` |
| D3 | 风格：print + assert + exit 0（同 m1） |
| D4 | 工程 README 加一行；**不**强改 UAT 门禁 |
| D5 | 理论 MD 不绑本 demo |

## Requirements

### T4 · 挤态 ⟨n⟩

| 列 | 值 |
|----|-----|
| 解析 | \(\sinh^2 r\) |
| G | 真空 → `squeeze(r)` → `mean_photon` |
| F | 同 r，高 cutoff（如 24）→ `mean_photon` |

容差：G 对解析 `1e-12`；F 对解析 `1e-3`（截断）。

### T1 · 相干 + loss

| 列 | 值 |
|----|-----|
| 解析 | \(T\|\alpha\|^2\) |
| G | `D(α)` → `loss(T)` → `mean_photon` |
| F | 同 α,T，cutoff 够大 → `loss` → `mean_photon(ρ)` |

可选第三列 B：`from_gaussian` 相干再 loss（同 G 通道，应 ≡ G）。  
**推荐含 B**：证明 G 通道与 B 逐组件同式。

参数草稿：`α=0.7`，`T=0.4`，F cutoff `≥20`。

### 输出形状（概念）

```text
M4 cross-rep
T4 squeeze <n>  r=...
  analytic | G | F
  ...
T1 coherent+loss  alpha=... T=...
  analytic | G | F | B
  ...
OK
```

## Acceptance Criteria

- [x] **AC-M1** m4 exit 0
- [x] **AC-M2** T4 G≡解析；F OK
- [x] **AC-M3** T1 G/F/B ≡ 解析
- [x] **AC-M4** README 链
- [x] **AC-M5** 无新物理；pytest 80

## Out of Scope

- T2 sample 统计 · T3 cat
- UAT U9
- 理论 MD 写 API

## Notes

- F 截断：α 不大、cutoff 够则 ⟨n⟩ 紧
- 失败信息打印各列，方便手对笔记
