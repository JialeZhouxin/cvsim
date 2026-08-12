# Design — Phase F5: Fock bridges + integration

## 目标与边界

Vision F5 三件套：交叉核对套件（atol 1e-7）/ threshold+PNR 双表示一致 / 双表示同一实验教程。
零新公开 API、零依赖、fock/gaussian/bridge 包零改动 — 纯测试 + 教程交付。

## 架构

### 1. `tests/test_fock_bridge_f5.py` — 交叉核对套件（R1）

**核对矩阵**（Gaussian 解析 ↔ Fock 数值）：

| 可观测 | Gaussian 侧（解析/闭式） | Fock 侧（数值） | 覆盖态 |
|---|---|---|---|
| PNR 分布 P(n) | `bridge.coherent_element(n)²` / `squeezed_element(n)²` / `thermal_diag(n)` | `fock.observables.pnrd_probs` | coherent/squeezed/thermal |
| ⟨n⟩ | `gaussian.observables.mean_photon`（½(⟨x²⟩+⟨p²⟩−1)）与闭式 |α|²/sinh²r/n̄ | 同上 + 有损链 |
| Threshold p_click | `gaussian.observables.p_click`（=1−`bridge.vacuum_probability`） | `1 − pnrd_probs[0]` | 同上 + 有损 η 扫掠 |
| 有损相干 ⟨n⟩ | η\|α\|²（闭式） | loss Kraus → mean_photon | η ∈ {0.1…0.9} |

**泄漏纪律（never-silent 规则落地）**：每个比较前断言截断 tail < 1e-9
（FockState.tail 工厂自带解析 tail；squeezed/thermal 用 1−Σp 或 tail 字段）；
tail 超限 → 测试直接 fail（"reject"），不静默比较。cutoff 选择：α=0.8 → N=40
（tail ~e-16）；r=0.5 → N=30（tail 3.9e-8 太近 → 用 tail 断言筛选，实测时取 tail<1e-9
的 cutoff，如 r=0.3 → N=30）。

**atol 基准（2026-08-12 实测）**：coherent/thermal 2.8e-16、squeezed 3.4e-8（纯泄漏）
→ 泄漏约束后 atol 1e-7 可达；squeezed 参数选 r ≤ 0.4 保证 tail 富余。

**测试结构**（mirror test_bridge.py 风格：parametrize + 泄漏注释）：
- `test_pnr_probs_coherent/squeezed/thermal`（parametrize α/r/n̄）
- `test_mean_photon_both_reps`（parametrize 三态 + 有损）
- `test_threshold_both_reps`（parametrize 三态）
- `test_lossy_coherent_eta_sweep`（η 参数化，⟨n⟩ + p_click 双断言）
- `test_leakage_discipline`（tail 断言本身的测试：截断不足必须 fail）

### 2. `tutorials/_build_08.py` + `tutorials/08_fock_bridge.ipynb`（R2）

mirror `_build_05/_build_07.py` 模式（md/code/notebook 辅助 + 写入路径）。5 节：
1. **设定**：同一实验双表示搭建 — coherent(α=0.8) 的 GaussianState 与 FockState（cutoff 40），loss(η) 两侧通道
2. **Threshold 检测**：p_click vs η 双曲线（Gaussian 解析 1−e^{−η|α|²} 线 + Fock 数值点），对账 + 误差标注
3. **PNR 分布**：η=0.5 处 P(n) 柱状（Poisson 解析 vs Fock 截断），mean_photon 两侧核对
4. **截断生存曲线**：max|ΔP(n)| vs cutoff ∈ {10,20,40,60}（α=0.8）— 截断误差指数衰减；泄漏标注
5. **结论**：bridge 规则（Gauss→Fock 闭式小 m、Fock→Gauss 容差内才成立；泄漏纪律）

### 3. 不动的东西

- `cvsim/bridge.py` / `cvsim/fock/*` / `cvsim/gaussian/*`：零改动
- FOCK_PUBLIC / ADR-0001 / pyproject：零影响
- `tests/test_bridge.py`：不动（F5 新套件独立文件）

## 兼容性

- 纯新增测试 + 教程，无任何签名/行为变化；923 测试回归面 = 0

## 风险与回滚

- 风险：squeezed 态泄漏与 atol 1e-7 打架 → 参数选 tail 富余区（r ≤ 0.4），泄漏断言先行
- 回滚：单 commit 可整体回退（纯新增文件）
