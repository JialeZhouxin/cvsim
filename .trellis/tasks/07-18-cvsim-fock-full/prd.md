# Fock 模拟器独立全流程

## Goal

Fock 独立闭环（本任务）：

```text
初态(1–2 模) → D/R/S/Kerr/BS → PNRD p(n) / norm / ⟨n⟩
```

单模路径 **向后兼容**。无损失、无 Fock Homodyne、无 Bosonic、无 Circuit。

## Background

- 现：`FockState.amps (N,)` + 单模 D/R/S + norm/⟨n⟩
- Gaussian 已独立闭环；Fock 需对等「能搭干涉 + 数光子 + Kerr」

## Decisions

| # | 决策 | 选择 |
|---|------|------|
| D1 | 轨道 | 独立 Fock |
| D2 | 范围 | **B：BS + Kerr + PNRD**（无 loss/Homodyne） |
| D3 | 存储 / BS | **2 模密集 `(N,N)` + 单模主路径保留**；m>2 不做 |

## Requirements

### 态

- **R1** 单模：`FockState.amps` shape `(N,)` 保持；`vacuum(cutoff)` 保持
- **R2** 两模：`FockState` 扩展 **或** 薄类型 `FockState2` / `nmode` + `amps` 秩 1 或 2  
  - 推荐：同一 `FockState`，`amps.ndim==1` 单模、`ndim==2` 两模，`cutoff` 每维相同
- **R3** `fock(n, cutoff)` / `fock2(n0, n1, cutoff)` 便捷初态（可选但建议）

### 门

- **R4** 单模：`displace` / `phase` / `squeeze` 继续；对两模态可 `mode=` 作用
- **R5** **`kerr(state, chi, mode=0)`**：`|n⟩ → e^{i χ n²} |n⟩`
- **R6** **`beamsplitter(state, theta, phi=0)`**：**仅 2 模**  
  - 标准：`U = [[c, e^{iφ}s], [-e^{-iφ}s, c]]` 作用在 ladder 生成元上，截断子空间 `expm` 或等价两模 unitary 作用振幅

### 测量 / 矩

- **R7** `pnrd_probs(state, mode=None)`：  
  - 单模：`p[n]=|c_n|²`  
  - 两模：`mode` 指定边缘；`None` 返回联合 `p[n0,n1]=|c|²`
- **R8** `norm` / `mean_photon` 支持 1–2 模（两模 `mean_photon(mode=)` 或总）

### 工程

- **R9** tests：`test_fock_kerr` / `test_fock_bs` / `test_fock_pnrd`（可合并）
- **R10** README Fock 节；quality 合同；全量 pytest + UAT 不破

## Acceptance Criteria

- [x] **AC-F1** 单模回归：挤 ⟨n⟩ / norm 旧测仍绿
- [x] **AC-F2** Kerr：`|n⟩` 相位 `e^{i χ n²}`
- [x] **AC-F3** `|1,0⟩ → BS(π/4)`：|c₁₀|²≈|c₀₁|²≈½
- [x] **AC-F4** 真空 2 模 → BS：仍真空
- [x] **AC-F5** PNRD：`∑p = norm`
- [x] **AC-F6** pytest 42 绿；UAT 5/5

## Out of Scope

- m≥3 张量；光子损失；Fock Homodyne；S₂ Fock；Bosonic；Hafnian；Circuit

## Open Questions

无阻塞项。BS 截断细节写 design（两模 Hilbert 维 N²，expm 可接受小 N）。
