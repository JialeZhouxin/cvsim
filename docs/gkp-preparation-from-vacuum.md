# GKP 从真空制备 — 技术可行性探测报告

**日期**: 2026-09-02 · **作者**: 会话探索(pi)
**背景**: bosonic 想从"手工拼分量"升级为"从真空经物理器件演化出 GKP"，需要推翻 vision §1.3 的 Kerr/PNR non-goal。本报告先用 **Fock 端**(已有精确 kerr/pnr/homodyne/ParamRef)探测哪些制备电路真正可行，为 PRD 提供数值依据。

---

## 1. 目标判据

"演化出 GKP" = 从真空出发，经物理门/测量，得到 x-边缘概率分布 `P(x)` 呈**梳状**：

- 峰位置在 `x = k·Δ`，`Δ = √(2π) ≈ 2.5066`（对照：手工 gkp0 峰位置确认在 `k·Δ`）
- 峰间距均匀 = Δ
- 高斯包络（峰高随 `|k|` 衰减）

## 2. 已确认的环境能力(Fock 端)

| 器件 | Fock 有? | bosonic 有? | 用途 |
|---|---|---|---|
| `squeeze` / `displace` / `phase` | ✅ | ✅ | 高斯基底 / 平移 |
| `two_mode_squeeze` / `beamsplitter` | ✅ | ✅ | 纠缠源 |
| `kerr` (`\|n⟩→e^{iχn²}\|n⟩`) | ✅ | ❌ | **非高斯，Route A 核心** |
| `measure_pnr` (光子数分辨) | ✅ | ❌ | **非高斯，Route B 核心** |
| `measure_homodyne` (φ=0 → 测 x) | ✅(单模) | ✅(多模) | 连续变量测量 |
| `ParamRef` feedforward (displace) | ✅ | ✅ | 条件位移 |
| `cz`/`cx` | ✅ | ✅ | 纠缠门 |

**结论**: Fock 端**器件齐全**，正是做这次探测的正确环境。bosonic 缺 kerr/pnr 两样非高斯器件。

## 3. Route A — Kerr 确定性制备（探测结果）

电路形如：`squeeze(r) → kerr(chi) → squeeze(-r)`，扫 `r` 与 `chi`。

### 实测
- 网格扫描 `r∈{0.8,1.0,1.2}` × `chi∈{0.2..3.0}` 共 24 组
- **对比度(contrast)普遍 ≥0.9** → 确实形成了周期性结构
- 但 **峰间距普遍 0.7–1.4**，不是目标 `Δ=2.5066`
- 最接近的只有 `r=1.2, chi=1.0` → 间距 1.83，仍偏离
- Fock 截断伪影：大 r 时纯 squeeze 也显示"15–21 峰"（截断振铃），"峰数"指标不可靠，需以峰间距+对比度为判据

### 判定
**单次 `squeeze+kerr+squeeze` 未找到标准 GKP(Δ=√(2π)) 参数窗口。** Kerr-GKP 需要特定精确参数匹配（如 `χ·r²` 关系），简单网格没扫到。这不是"不可能"，而是需要文献参数窗 + 精细扫描。

## 4. Route B — 测量 + 条件位移（探测结果）

电路形如：`two_mode_squeeze(r) → measure_?(ancilla) → displace(mode0, ParamRef)`。

### 实测
- `two_mode_squeeze(0,1,r) → measure_pnr(1)` 单次后选(m_n=0) → mode0 是**单个高斯态**(挤压真空，**无梳**)
- 单次 PNR 后选 → n=0 给出真空，n=1.. 给出不同 Fock 态，**不产生叠加梳**

### 判定
**单次测量后选不产生 GKP 梳。** 需要**多次后选的平均/叠加**（概率性制备，post-selection over a distribution of outcomes）——这正是 GKP 概率制备的本质，也解释了为什么 vision 标它"more convoluted"。

## 5. 当前受限项

- **fock homodyne_sample 仅支持单模**(mode 必须为 0) → 两模 homodyne 测量需绕行或改后端。PNR 无此限制(支持任意 mode)。
- **Fock 截断**: cutoff 有限时无限梳 GKP 有截断误差；cutoff=14 两模已 K² 爆炸，需更大 cutoff 才接近真 GKP。

## 6. 核心结论

| 路线 | 能否出梳 | 障碍 | 复杂度 |
|---|---|---|---|
| A. Kerr (`sq+kerr+sq`) | ⚠️ 有周期结构但间距≠Δ | 需要特定参数窗+精细扫描；Fock 截断 | 中 |
| B. PNR+条件位移 | ❌ 单次后选只给单高斯 | 需多次后选叠加(概率制备) | 高 |
| 手工拼分量(现状) | ✅ 直接是 Δ 梳 | 非"演化",是构造 | 低 |

**物理根源**: GKP 是**非高斯态**，从真空生成需要非高斯操作(Kerr/PNR)，而这些操作在连续变量下生成 GKP 需要**精细参数匹配**或**概率性多结果后选**——**不是随手搭电路就能成的**。这是 vision §1.3 把 Kerr/PNR 列 non-goal(标"more convoluted than Gaussian")的根本原因，探测证实了这一点。

## 7. 建议决策路径(待定)

**方案 ① 尊重 vision，走教学叙事(最省)**
- bosonic 保持"高斯门+工厂+测量"，`gkp0/gkp1` 继续手工构造
- 用 Fock 端(已有 kerr/pnr)演示"真实非高斯制备"，但**只作为教学对照**，不做 bosonic 演化
- 代价：几乎零新代码；但 bosonic 无法"演化"GKP

**方案 ② 坚持 bosonic 演化，先攻克参数窗(中)**
- 先研究 Kerr-GKP 文献参数关系(而非盲扫)，锁定能出 `Δ=√(2π)` 梳的 `(r, chi)` 
- 再在 bosonic 加 kerr 门(分量近似)，RN 等验证能复现同样梳
- 代价：探索成本高，且分量近似 kerr 有额外误差

**方案 ③ 先立 PRD 但把探测列为 Phase 0(推荐)**
- PRD 明确目标"bosonic 演化出 GKP"、范围、验收(以 Fock 端 gold 锚保真度)
- Phase 0 = 继续探测锁定参数窗(Route A 用文献参数,Kerr-GKP)
- Phase 1 = bosonic 加 kerr(分量近似) + 用 Fock 校验
- 关键风险：分量近似 kerr 是否能复现 Fock 精确结果，需 Phase 0 验证

---

## 附录：探测工具

- `tools/probe_gkp_kerr.py` — Route A Kerr 扫描(x-边缘 + 梳状评分)
- `tools/probe_gkp_pnr.py` — Route B PNR/homodyne 制备探测(部分完成)
