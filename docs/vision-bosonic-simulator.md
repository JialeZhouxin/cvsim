# Vision: Production Bosonic Simulator

> **Audience:** AI coding agents and human maintainers.
> **Role:** Single source of truth for *what to build* and *what must not drift* — for the Bosonic representation.
> **Not:** An implementation changelog. When code and this doc disagree, **this doc wins for greenfield work**; tasks must implement the spec or explicitly amend this doc first.
> **Sibling:** Gaussian story lives in [`vision-gaussian-simulator.md`](./vision-gaussian-simulator.md); Fock peer in [`vision-fock-simulator.md`](./vision-fock-simulator.md). Cross-representation rules owned by Gaussian vision §6 unless amended here.

**Last updated:** 2026-08-14
**Status:** Vision locked by grill (Q1–Q13, 2026-08-13); **B0–B1 done (2026-08-14)**：基线冻结 + 能力完备（门全集/通道/heterodyne+threshold/coherent 工厂/BOSONIC_PUBLIC 冻结 33 名）；B2 组件工程 next
**Codebase today:** `cvsim/bosonic` B1 生产面（state/cat/gkp/gates 11 门/channels 3/measure.py 三测量/observables 矩；单模 homodyne 教学切，B3 换精确）

---

## 0. 一句话

Bosonic 模拟器 = **第三个生产级表示模拟器**（peer to Gaussian/Fock）：后端把 GKP 纠错这类"高斯门 + 测量 + 反馈"的非高斯故事跑得又快又准（O(K·m²)），前端复用 Gaussian/Fock 同壳 GUI 做 GKP 纠错教学展示。

---

## 1. Purpose & non-goals

### 1.1 Purpose

Build a **production-grade Bosonic-basis simulator, peer to the Gaussian and Fock ones**: complete capability surface (gates / channels / measures / analyse / circuit DSL + IR), honest single-mode scale anchor, and a **component-engineering discipline** (merge / truncate / underflow / normalization) as the cross-cutting constraint. The front-end reuses the Gaussian/Fock shared shell; the teaching surface is the GKP error-correction story.

### 1.2 Why peer-level

Gaussian's "production" claim rests on scale + precision (m→100, fast compile). Fock's rests on precision + capability completeness (quantified truncation). Bosonic's claim rests on **non-Gaussian states at Gaussian-like cost**: cat/GKP stay a few hundred components instead of exploding Fock cutoffs. The three are complementary ledgers for one physical story (§6).

### 1.3 Non-goals (locked 2026-08-13)

| Excluded | Note |
|----------|------|
| **Kerr / arbitrary non-Gaussian gates in component form** | Selection table verdict: Kerr continuous twisting → Fock. Bosonic eats Gaussian gates + factories + measurements only |
| **Protocol library** (e.g. built-in GKP QEC rounds) | P1 locked: bricks in the library, protocols in tutorials / GUI scripts. Library must not grow into an error-correction framework |
| **Multi-mode production-grade** | A1 locked: single-mode production anchor; architecture written for arbitrary m; dual-mode is an open question (K² blowup is real engineering, no scene driving it yet) |
| **Component-form PNR path** | M1 locked: PNR teaching scenes switch to Fock. Component PNR is "theoretically possible, more convoluted than Gaussian" (notes §5.4) — open question |
| **AD (differentiable)** | Open question. Component-weight differentiability is heavy engineering; GKP teaching doesn't need it |
| **Tensor networks / cloud / multi-user** | Inherits Fock stance, no re-litigation |

---

## 2. Conventions

### 2.1 State representation (frozen at teaching-MVP)

- **State:** `BosonicState` = list of `Component` triples `(V_k, r̄_k, w_k)`:
  - `V_k` — `2m×2m` real covariance (xxpp, ħ=1, same as Gaussian)
  - `r̄_k` — `2m` **complex** displacement (imaginary part encodes coherence/interference center)
  - `w_k` — **complex** weight (diagonal terms real-positive; cross terms complex, e.g. cat interference)
- **Normalization:** conceptually Σ_k w_k relates to the trace (notes §2.1); `weight_sum(state) == 1` for a normalized decomposition.
- **Gaussian is the K=1 special case:** `from_gaussian` wraps `(V, r̄)` as one component w=1.

### 2.2 Quadrature / phase conventions

- Follows Gaussian vision §2 (ħ=1, xxpp, displacement √2 scaling) — same `conventions` / `symplectic` root modules.
- Gates act per-component: `V_k ↦ S V_k Sᵀ`, `r̄_k ↦ S r̄_k + d` (Gaussian affine per component).

### 2.3 Measurement semantics

- **Homodyne:** per-component affine + likelihood reweighting (teaching closed form, notes §5.2). B3 upgrades sampling to **exact edge distribution** (cross terms included, no "diagonal-peak pool" approximation — that is the teaching cut, explicitly not production). **Sampling strategy (A5, 2026-08-14): CDF grid inversion** — P(x) = Σ_k w_k p_k(x) 是复权重混合（无正概率权重，拒绝采样不可行）；网格 δx ≤ σ_min/5 自动定，uniform + searchsorted 反演，10³ shots 向量化；条件化 ρ_post = Σ_k [w_k p_k(x)] ρ_k / P(x) 同一核。
- **Heterodyne / threshold:** follow Gaussian semantics (threshold = outcome-only {0,1}, no state update; heterodyne conditions and deletes the measured mode).

---

## 3. Architecture

```text
cvsim/
  conventions.py         # shared (ħ=1, xxpp) — exists
  symplectic.py          # shared symplectic core — exists
  circuit_common.py      # shared DSL core (op list, params, compile traversal, ParamRef) — exists (ADR-0004)
  bosonic/
    state.py             # BosonicState + Component (V, r̄ complex, w complex) — exists
    cat.py               # even_cat / odd_cat — exists
    gkp.py               # gkp0 / gkp1 / gkp_logical_overlap — exists
    gates.py             # displace/phase/squeeze/beamsplitter/two_mode_squeeze — exists; align full Gaussian gate set in B1
    channels.py          # loss — exists; amplifier/phase_noise align in B1
    observables.py       # 矩 only: mean_photon — exists（A4: homodyne 已迁 measure.py）
    component_eng.py     # B2: merge / truncate / underflow / normalization + 组件截断泄漏 + is_hermitian（A3）
    measure.py           # 全部测量（A4 合并，对齐 Gaussian）: homodyne mean/var/sample/condition（B3 精确采样 = CDF 网格反演）+ heterodyne/threshold（B1）— homodyne 部分 exists
    analyse.py           # B2/B4: purity / entropy / fidelity (component-weighted, private to bosonic — ADR-0001)
    circuit.py           # B5: BosonicCircuit (arbitrary m, component-wise execution)
    ir.py                # B5: to_ir/from_ir (circuit_v1 roundtrip)
```

**Shared circuit framework (Q/B1):** `circuit_common` gains its **third consumer** — `BosonicCircuit` instantiates it with the Bosonic gate/measure registry, fulfilling the ADR-0004 generalization commitment (Fock was the second consumer).

---

## 4. Phased roadmap & exit criteria

Ordering principle: **dependency order first, each phase ships a demo exit** (mirrors Gaussian §5 / Fock §4).

### B0 — Baseline freeze (existing teaching MVP)

**Has:** `BosonicState`/`Component` (complex r̄/w), even/odd cat, gkp0/gkp1 + logical overlap, 5 gates, loss, homodyne mean/var/sample/condition, mean_photon.

**Exit:** freeze §2 conventions; any change is major-version territory. Test harness for existing surface in place.

### B1 — Capability completeness

**Build:** full Gaussian gate set per-component (fourier/mz/cz/cx/interferometer align), amplifier / phase_noise channels, **heterodyne + threshold** (M1), factory completion.

**Exit criteria**

1. Gate set 1:1 aligned with Gaussian vision named gates; per-component affine matches Gaussian results for K=1 (atol).
2. Heterodyne / threshold semantics match Gaussian counterpart (same outcome distribution for K=1).
3. `pytest` green; no convention drift.

### B2 — Component engineering (C2 core, dark work)

**Build:** near-peak merge / small-weight truncation (amp_cutoff knob) / underflow handling / normalization discipline + **component truncation leakage metric** (Bosonic's answer to Fock's truncation leakage).

**Exit criteria**

1. Merge/truncate preserves Wigner fidelity within budget (measure the tradeoff curve).
2. Leakage metric API: warn > threshold, fail > hard ceiling (mirrors Fock §5).
3. Budget table for K / ε calibrated (target: K ≤ a few hundred, ε ≥ 0.05 single-mode).

### B3 — Measurement precision (C3 main engineering)

**Build:** homodyne **exact edge distribution + exact conditional** — replace the teaching "diagonal-peak pool" sampling with the full interference kernel (complex centers + complex weights).

**Exit criteria**

1. Exact edge distribution matches Fock high-cutoff P(x) for cat/GKP atol (cross-check, R1 layer 2).
2. Conditional posterior Σ_k w_k L_k → normalized; consistency identity Σ p(o)·ρ_post(o) = ρ.
3. Sampling histogram vs exact density agreement (KS or bin-level).

### B4 — Reconciliation suite (R1, layered)

**Build:** layered verification: (layer 1) degenerate cases vs analytic/Fock closed forms atol 1e-7 (K=1 Gaussian, small cat 4-component vs Fock, coherent/thermal single component); (layer 2) GKP internal identities (logical fidelity identities, "measure then feed back = untouched" self-consistency, post-recovery fidelity monotonicity) + Fock high-cutoff cross-check. Honest annotation: GKP has **no analytic benchmark**; layer-2 is mutual numeric verification.

**Exit criteria**

1. Layer-1 hard atol suite green.
2. Layer-2 identity suite green with documented tolerances.
3. Docs state the no-analytic-benchmark caveat for GKP.

### B5 — BosonicCircuit (B1 decision)

**Build:** arbitrary-m circuit, component-wise execution, to_ir/from_ir roundtrip (circuit_v1), shared `circuit_common` third consumer.

**Exit criteria**

1. Compiled vs naive identical on fixtures (K ≤ few hundred, m=1).
2. IR roundtrip lossless (golden fixtures).
3. Lab `backend="bosonic"` path consumes circuit_v1 without schema change.

### B6 — GUI (G1 three-piece)

**Build:** same-shell third backend (`backend="bosonic"`): palette whitelist + result panel = **Wigner evolution view** (B) + **fidelity sweep curve** (A, γ scan) + **step execution** (C, intermediate state inspectable after each conditional — new GUI capability, not in Fock F7).

**Exit criteria**

1. GKP QEC main script (gkp0 → loss γ → homodyne → feedforward → fidelity curve) ≤5 min without handwritten Python.
2. Golden fixture: Bosonic JSON → `/run` matches equivalent script (atol).
3. Old Gaussian/Fock JSON behavior unchanged; pytest + node suite green.

### B7 — Bridges + tutorials

**Build:** Gaussian↔Bosonic (trivial K=1 wrap), Fock↔Bosonic reconciliation tutorial (cat/GKP cross-check), QEC teaching notebook (protocol lives here, per P1).

**Exit criteria**

1. Bridge cross-check suite atol 1e-7 (small K).
2. Tutorial: same physical experiment in all three representations, numbers reconciled.
3. Notebook Run-All green.

---

## 5. Component engineering (cross-cutting, C2)

Every Bosonic result must answer: *what did component management cost?*

1. **Leakage metric:** weight mass discarded by truncation (amp_cutoff) + merge distortion estimate.
2. **Default:** warn when discarded mass > threshold (default 1e-6 configurable); fail > 1e-3 strict — mirrors Fock §5.
3. **Never silently truncate:** no hidden merge/truncate inside gates; explicit API only.
4. **Normalization discipline:** periodic renormalization by trace; track drift.
5. **Underflow:** complex-weight underflow (large |α| cross terms) → explicit drop with leakage accounting.

## 6. Relationship to Gaussian / Fock

- **Shared:** conventions, symplectic, `circuit_common` DSL core, testing doctrine.
- **Gaussian↔Bosonic:** trivial — K=1 wrap (`from_gaussian`). Bosonic gates *are* Gaussian affine per component.
- **Fock↔Bosonic:** reconciliation via R1 layer 2 (cat/GKP cross-check at high cutoff); no silent conversion inside gates (Gaussian vision §6 rules hold).
- **No rep-switching inside gates:** conversion explicit, at boundaries only.

## 7. Performance & numerics budget

| Topic | Rule |
|-------|------|
| Dtype | float64 default; complex r̄/w tracked separately |
| Anchor | m=1 production-grade, K ≤ a few hundred (ε ≥ 0.05) — calibrate in B2 |
| Architecture | arbitrary m written; dual-mode K² cost documented as open question |
| Batch shots | 10³ homodyne normal; allocate once |
| Leakage | warn >1e-6 default; fail >1e-3 strict |
| Memory | K·m² per component set; 300 components × 2×2 V ≈ negligible; multi-mode budget in benchmarks |

**Numerical hygiene for agents**

- Track complex displacement separately from real part; never silently drop imaginary parts.
- Renormalize weights after every conditional; check weight_sum.
- Always check component leakage after truncation/merge (warn path).
- No new hard deps beyond numpy/scipy.

## 8. Testing doctrine

Every `B-*` feature needs:

1. **Unit:** math identities (e.g. K=1 reduces to Gaussian).
2. **Invariants:** normalization / trace preservation / reweighting consistency.
3. **Golden:** fixed-seed snapshots for samplers; cat/GKP Wigner slices.
4. **Regression:** tutorials import public API only.
5. **Cross-representation:** R1 layer 1 hard atol vs Gaussian/Fock (B4).

Marker idea: `@pytest.mark.phaseB1` etc. — mirror Gaussian §9 / Fock §8.

## 9. Gap snapshot (current repo)

| Feature | Now | Gap |
|---------|-----|-----|
| State factories | BosonicState/Component + even/odd cat + gkp0/gkp1 + coherent | —（B1 done） |
| Gates | 11 门（D/R/S/F/BS/MZ/S₂/CZ/CX/interferometer）K=1 atol 对齐 | —（B1 done） |
| Channels | loss/amplifier/phase_noise（X,Y 逐分量仿射） | —（B1 done） |
| Measures | measure.py：homodyne 教学切（mean/var/sample/condition）+ heterodyne 教学切 + threshold outcome-only | exact edge + conditional + 混合态 heterodyne 精确化（B3） |
| Component engineering | — | merge/truncate/underflow/normalization + leakage + is_hermitian（B2） |
| Analyse | mean_photon | purity/overlap/pure_fidelity 闭式（B2/B4）；entropy defer |
| Circuit DSL | — | BosonicCircuit + IR + run_steps（B5） |
| Reconciliation | — | R1 layered suite（B4） |
| GUI | — | G1 three-piece（B6） |
| Bridges | from_gaussian wrap | B7 |

## 10. Open questions

1. **Dual-mode production-grade** (A1 defer): K² component blowup — real engineering, no scene driving it yet. Unlock condition: a dual-mode GKP teaching scene or surface-code story.
2. **Component-form PNR** (M1 defer): theory path exists (notes §5.4), more convoluted than Gaussian. Unlock: a scene where PNR must stay in Bosonic.
3. **AD / differentiability**: component-weight gradient engineering. Unlock: a design loop that needs Bosonic gradients.
4. **Tensor networks**: long-term research item, not committed (inherited).

## 11. Document control

| Version | Date | Change |
|---------|------|--------|
| 0.1.0 | 2026-08-13 | Vision created from grill Q1–Q13: GKP QEC teaching main stage + production backend; C1–C4 pillars; A1 single-mode anchor (arbitrary-m architecture); R1 layered reconciliation; P1 bricks-not-protocols; M1 measure surface; B1 circuit third consumer; G1 GUI three-piece; B0–B7 roadmap; non-goals (Kerr/protocols/multi-mode/PNR/AD) |
| 0.1.1 | 2026-08-14 | 架构层 amend（grill A1–A12，任务 08-14-bosonic-architecture）：A4 测量并入 measure.py（observables 只留矩）；A5 homodyne 精确采样策略锁 CDF 网格反演（§2.3）；组件工程补 is_hermitian（A3）。详见 design.md + ADR-0006 |
| 0.2.0 | 2026-08-14 | **B0–B1 done**（任务 08-14-bosonic-b1，commit `fe94357`）：门全集 11（K=1 atol 1e-10）、通道 3、measure.py（homodyne/heterodyne 教学切 + threshold outcome-only）、coherent 工厂、BOSONIC_PUBLIC 冻结 33 名、phaseB1 markers；全套 1059 passed。§0 状态 / §9 gap 表同步；契约层 `.trellis/spec/cvsim/` 新建 |
