# Vision: Production Fock Simulator

> **Audience:** AI coding agents and human maintainers.
> **Role:** Single source of truth for *what to build* and *what must not drift* — for the Fock representation.
> **Not:** An implementation changelog. When code and this doc disagree, **this doc wins for greenfield work**; tasks must implement the spec or explicitly amend this doc first.
> **Sibling:** Gaussian story lives in [`vision-gaussian-simulator.md`](./vision-gaussian-simulator.md). This doc is the Fock peer; cross-representation rules (bridges) are owned by the Gaussian vision §6 unless amended here.

**Last updated:** 2026-08-11
**Status:** Vision locked by brainstorm (Q1–Q12, 2026-08-10); **F1–F3 complete (2026-08-11)**; F4+ open
**Codebase today:** `cvsim/fock` — F1–F3 landed（见下节）

---

## 0. Implementation status (2026-08-11)

F1–F3 切片已全部落地并归档（`.trellis/tasks/archive/2026-08/08-11-cvsim-phase-f*`）；以下愿景正文 F4+ 部分仍然有效。

| 切片 | 内容 | 代表 commit |
|------|------|-------------|
| **F1** factories/gates/channels | `FockState`/`FockDensity`（m=1–4）+ 11 门（D/R/S/BS/S₂/Kerr/CZ/CX/MZ/interferometer/…）+ loss/amplifier/phase_noise/apply_kraus + `circuit_common` 共享核 | `34f3fb6` `07fc7ab` |
| **F2** analyse/measure/api-freeze | entropy_vn/log_negativity/fidelity/partial_trace + pnr/homodyne/heterodyne（sample/condition）+ generic-m + **FOCK_PUBLIC 冻结**（35 导出） | `15c3815` `c355443` `9b7e432` |
| **F3** circuit/ir/batch/sparse | `FockCircuit`（任意 m、per-mode cutoffs、Kronecker 逐 op）+ `to_ir`/`from_ir` + `pnr_sample_batch`（10³ 向量化）+ `FockSparse`（COO，m≤10 锚） | `4d95065` `5057149` `60e2119` `3f4b132` |

**验证**：19 个 Fock 测试文件，165 passed（2026-08-11 复核）。

---

## 1. Purpose & non-goals

### 1.1 Purpose

Build a **production-grade Fock-basis simulator, peer to the Gaussian one**: complete capability surface (gates / channels / measures / analyse / circuit DSL + compile / dual backend + AD), honest small-mode scale anchor, and a **truncation-engineering discipline** as a cross-cutting constraint. Not a Gaussian re-skin — Fock's unique physics (PNR, Kerr, photon statistics, truncation) is the product.

### 1.2 Why peer-level

The Gaussian simulator's "production" claim rests on scale + precision (m→100, fast compile). Fock cannot scale (N^m); its "production" claim rests on **precision + capability completeness**: every Gaussian capability has a Fock counterpart, and every Fock result carries a **quantified truncation error**. The two representations are complementary tools for one physical story (§6).

### 1.3 Non-goals (locked 2026-08-10)

| Excluded | Note |
|----------|------|
| Boson-sampling **algorithm racing** (sampling-speed optimization, commercial GBS) | Simulator ships PNR sampling capability (F3); algorithms are users' business (Gaussian side: GBS = adapter, same stance) |
| **Tensor-network representations** (MPS/MPO) | Sparse extension (Q6) caps at m≤10+ with sparse arrays; tensor nets are another magnitude of numerical engineering — listed as long-term research item, **not committed** |
| Arbitrary states with m>10 | Q6 hard anchor |
| Cloud / multi-user service | Same stance as Gaussian + Lab vision |
| Fock GUI | Short-term excluded; **long-term required + compatibility assessment** (Q9, open) |

---

## 2. Conventions

### 2.1 State representation

- **Pure state:** amplitude tensor `amps`, shape `(N,)` (1 mode) or `(N0, N1)` (2 mode), Fock-basis coefficients `c[n0, n1, ...]`. Cutoff `N` per mode (global or per-mode — per-mode landed in F3 `FockCircuit`).
- **Density:** `FockDensity` matrix, 2-mode originally; general m=1–4 landed (F2 generic-m).
- **Truncation leakage** (cross-cutting): for pure state `leak = 1 − ‖amps‖²`? No — amplitudes are stored truncated and renormalized; leakage is defined against the *untruncated* state, available only analytically (cat/coherent/squeezed/thermal have closed-form tails) or via higher-cutoff comparison. **API:** `truncation_leakage(state)` returns an estimate (analytic tail for factory states, higher-cutoff comparison otherwise); gates check it (Q7).

### 2.2 Quadrature / phase conventions

- Follows Gaussian vision §2 (ħ=1, xxpp) — same conventions module; Fock gates use the same `phase` convention (displace `α`, squeeze `r`, BS `θ/φ`).
- `annihilation` matrix in `cvsim/fock/gates.py` is the reference for a/a†.

### 2.3 Cutoff semantics

- `cutoff` = Hilbert-space dimension per mode (N = 0..N−1 Fock levels).
- No hidden cutoff promotion inside `cvsim.fock.gates` (mirror: "Never silently truncate Gaussians into Fock inside gaussian.gates"); explicit API only.

---

## 3. Architecture

```text
cvsim/
  conventions.py         # shared (ħ=1, xxpp) — already exists
  fock/
    state.py             # FockState + factories (vacuum/fock/fock2/coherent/squeezed/cat, m=1–4) + leakage API — done F1–F2
    density.py           # FockDensity (thermal/from_pure, m=1–4) — done F2
    gates.py             # 11 named gates + apply_unitary — done F1; backend= parametrization is F4
    channels.py          # loss/amplifier/phase_noise/apply_kraus — done F1
    observables.py       # norm/⟨n⟩/pnrd_probs/homodyne/heterodyne/PNR sample+condition+batch — done F1–F3
    analyse.py           # entropy_vn/log_negativity/fidelity/partial_trace — done F2
    circuit.py           # FockCircuit — arbitrary m, per-mode cutoffs — done F3
    ir.py                # to_ir/from_ir (circuit_v1 roundtrip; compile landed as IR — no separate compile.py) — done F3
    sparse.py            # FockSparse (COO, m≤10 anchor) — done F3
  circuit_common.py      # shared DSL core (Q5): op list, params, compile traversal, ParamRef — exists
  interop/               # existing ordering + Fock SF interop (F6)
  bridge.py              # observation bridge — formal bidirectional API is F5
```

**Shared circuit framework (Q5):** `circuit_common` holds the representation-agnostic machinery (op list, parameter resolution, compile traversal, ParamRef). `GaussianCircuit` and `FockCircuit` instantiate it with their own gate/measure registries. This reverses the Phase 5 "no CVCircuit" YAGNI decision — justified because the second consumer now actually exists. Gaussian regression surface (758+ tests) is the safety net.

---

## 4. Phased roadmap & exit criteria

Mirrors the Gaussian phase structure (Q4). Each phase ships a demo exit.

### F0 — Baseline (done: teaching MVP)

**Has:** FockState/FockDensity (1–2 mode), gates (squeeze/phase/displace/kerr/BS/tms), loss channel (Kraus), observables (norm/trace/mean_photon/pnrd_probs/homodyne incl. condition), bridge elements, 2 notebooks.

**Exit:** freeze current conventions (§2); any change is major-version territory.

### F1 — Core completeness (done 2026-08-11)

**Build:** factories (cat/coherent/squeezed/thermal with analytic tails), missing gates (interferometer/MZ/CZ/CX per Fock qudit encoding), channels (amplifier, phase_noise), truncation-leakage API + checks (Q7), per-mode cutoff.

**Exit criteria**

1. All core factories/gates/channels public with docstring math.
2. Leakage API returns analytic tails matching high-cutoff comparison (golden).
3. `pytest` green; no convention drift.

### F2 — Analyse + measure (done 2026-08-11)

**Build:** entropy_vn / log_negativity / fidelity / partial_trace; heterodyne (sample + condition); **PNR condition** (posterior state update on photon-count outcome); density for general m.

**Exit criteria**

1. Research quantities match analytic Fock states (cat, Fock, thermal).
2. PNR condition: posterior norms sum to 1; Σ p(n)·ρ_post(n) = ρ (consistency identity).
3. Teaching notebook Run-All (PNR statistics + conditioning).

### F3 — Compile, sample, truncation engineering (done 2026-08-11)

**Build:** FockCircuit (shared framework), compile (merged unitaries, no merge across noise/measure), PNR batch sampling (vectorized, seeded), **sparse amplitude representation** (sparse arrays for photon-number-sparse states, m≤10+), scale budget tests.

**Exit criteria**

1. Compiled vs naive identical on fixtures (m≤4).
2. Sparse vs dense identical on cat/GKP/single-photon states within budget.
3. 10³ PNR shots API stable; truncation budget documented (see §7).

### F4 — Differentiable designer

**Build:** `backend=` numpy/jax parametrization of gates/measures; Fock AD (gradients w.r.t. squeeze/BS/Kerr), one optimization notebook (e.g. maximize Kerr-squeezed state fidelity under loss).

**Exit criteria**

1. Gradients agree with finite difference (squeeze/BS/Kerr) — mirror Gaussian Phase 4 bar (2e-07).
2. Numpy and JAX paths share tests via backend parametrization.

### F5 — Bridges + integration

**Build:** observation bridge promoted to formal bidirectional API (Q11): element-level conversion (done in `bridge.py`), observable propagation, threshold/PNR cross-checks; Gaussian-vision §6 rules kept (Fock→Gauss only within tolerance, else reject).

**Exit criteria**

1. Bridge cross-check suite: Gaussian analytic vs Fock numeric agree atol 1e-7 (small m).
2. Threshold (p_click) and PNR expectations agree where both apply.
3. Tutorial: same physical experiment simulated in both representations, results reconciled.

### F6 — Interop

**Build:** Fock ↔ external tools (Strawberry Fields `[sf]` extra, round-trip golden), density-matrix export format documented.

**Exit criteria**

1. Round-trip golden tests (no runtime dep on external tools).
2. Interop docs with copy-paste scripts (mirror `docs/sf-roundtrip.md`).

---

## 5. Truncation engineering (cross-cutting, Q3/Q7)

Every Fock result must be able to answer: *what is the truncation error?*

1. **Leakage metric:** tail probability estimate per state — analytic tail for factory states (coherent: `1 − Γ(N,|α|²)`, etc.), higher-cutoff comparison otherwise.
2. **Default:** operations warn (`RuntimeWarning`) when leakage > threshold (default 1e-6 configurable).
3. **Strict mode:** `validate=True` (or leakage > hard ceiling 1e-3) raises `ValueError` — mirrors Gaussian `validate_state(validate=...)`.
4. **Never silently truncate:** no hidden cutoff promotion inside gates (rule 2.3); explicit API only.
5. **Error propagation:** documented upper bounds — leakage bounds PNR mean error and homodyne moment error (see §7).

## 6. Relationship to Gaussian (Q5, Q11)

- **Shared:** conventions, `circuit_common` DSL core, `interop` ordering, testing doctrine.
- **Bridges:** §6 rules from Gaussian vision hold (Gauss→Fock closed-form small m; Fock→Gauss detect-and-reject; never silent). Observation bridge (Phase 5 F-BRIDGE) elevates to formal API in F5.
- **No rep-switching inside gates:** each representation evolves its own states; conversion is explicit and at boundaries only.

## 7. Performance & numerics budget

| Topic | Rule |
|-------|------|
| Dense anchor | m≤4 exact-grade (cutoff 20–40, per-mode) |
| Dense ceiling | m=6 documented upper bound; beyond → explicit rejection (fail-fast) |
| Sparse extension | photon-number-sparse states via sparse arrays, m≤10+; identical physics vs dense |
| Batch shots | 10³ PNR normal; allocate once |
| Leakage | warn >1e-6 default; fail >1e-3 strict |
| Backend | float64 default; jax parity from F4 |
| Memory | dense 2-mode 40×40 complex ≈ 50 KB; 4-mode 40⁴ ≈ 200 MB — budget table in benchmarks |

**Numerical hygiene for agents**

- Always check leakage after noisy updates (warn path).
- Symmetrize density after every noisy update.
- No new hard deps beyond numpy/scipy; jax and external tools stay optional extras.

## 8. Testing doctrine

Every `F-*` feature needs:

1. **Unit:** math identities (e.g., commutation, unitarity).
2. **Invariants:** unitarity / CP / trace-preservation where applicable.
3. **Golden:** analytic tails, PNR expectation identities, closed-form states.
4. **Regression:** tutorials import public API only; leakage checks in CI sample.
5. **Cross-representation:** bridge checks against Gaussian analytic values (F5).

Marker idea: `@pytest.mark.phaseF1` etc. — mirror Gaussian §9.

## 9. Gap snapshot (current repo)

| Feature | Now | Gap |
|---------|-----|-----|
| State factories | vacuum/fock/fock2/coherent/squeezed/cat + leakage API | —（F1 done）；thermal 在 `FockDensity` |
| Gates | 11 门（D/R/S/BS/S₂/Kerr/CZ/CX/MZ/interferometer/…） | `backend=` (F4) |
| Channels | loss/amplifier/phase_noise/apply_kraus | —（F1 done） |
| Measures | homodyne/heterodyne/PNR（sample/condition/`pnr_sample_batch` 10³） | —（F1–F3 done） |
| Analyse | entropy_vn/log_neg/fidelity/partial_trace | —（F2 done） |
| Circuit DSL | FockCircuit（任意 m，per-mode cutoffs） | —（F3 done） |
| Compile | `to_ir`/`from_ir` roundtrip（IR 形式落地） | —（F3 done） |
| Sparse | FockSparse（COO，m≤10） | —（F3 done） |
| AD | — | backend= + gradients (F4) |
| Bridges | bridge.py elements | formal bidirectional API (F5) |
| Interop | — | SF round-trip (F6) |

## 10. Open questions

1. **Fock GUI (Q9):** long-term required; compatibility with the Gaussian Lab GUI (shared `circuit_v0` JSON schema evolution, editor whitelist, backend abstraction) **to be assessed** — assessment gated on simulator roadmap completion (F3+). Until then: no Fock GUI (Lab vision locked).
2. **Tensor networks:** long-term research item, not committed (§1.3).
3. **General-m density:** F2 assumes m up to 4 dense; density for m>4 deferred to sparse era.

## 11. Document control

| Version | Date | Change |
|---------|------|--------|
| 0.2.0 | 2026-08-11 | F1–F3 落地：架构树 / gap 表 / roadmap 同步至实现状态（commit 链 `34f3fb6`…`3f4b132`，165 tests） |
| 0.1.0 | 2026-08-10 | Vision created from brainstorm Q1–Q12 (user: production-grade, peer to Gaussian; shared circuit framework; hard scale anchor + sparse extension; truncation discipline; GUI long-term + compatibility assessment open) |
