# Bosonic B6 GUI 三件套——same-shell 第三 backend

## Goal

Lab GUI 扩为 **Gaussian/Fock/Bosonic 同壳三后端**（`backend="bosonic"`）：palette whitelist + 结果面板 = **Wigner evolution view** (B) + **fidelity sweep curve** (A, γ scan) + **step execution** (C)。教学主视觉 = **GKP 位移纠错**（gkp0 → CZ → loss γ → homodyne → feedforward → fidelity curve）。

## Requirements

### R1. Bosonic IR `initial` 态源（Q1/Q5 锁）

- IR `initial` 扩展字段（B5 `EXTENSION_FIELDS` 已占位）具体化：per-mode 态名列表 `["gkp0", "gkp1"]`，`null`/缺省 = 真空。只支持**无参态**（`gkp0`/`gkp1`/真空）。
- `BosonicCircuit(initial=...)` 构造参数：接受 `BosonicState | None` 或态名列表；K=1 恒定锁不受影响（initial 在此之上；gate 仍不增分量）。
- 缺省 `initial`（无字段/全 null）= vacuum（与 B5 行为一致，旧 JSON 零破坏）。

### R2. GKP QEC 主脚本（Q2 锁，exit 1）

```
initial: [gkp0, gkp1]     # mode0=data |0⟩_GKP, mode1=ancilla |1⟩_GKP
cz(0, 1)
loss(0, γ)                # γ 扫溜 0→0.5
homodyne(1, x) → outcome u
displace(0, gain·u)       # feedforward，gain GUI 可调
final: data mode 0 态
fidelity(final, ideal gkp0) → 曲线
```

GUI 内**无手写 Python**搭出并跑通 ≤5 min。

### R3. `pure_fidelity` 双 V 升级（Q3 锁）

- `_gauss_overlap` 升**通用双 V**：`2^m·(detVa·detVb)^{1/4}/√det(Va+Vb)·exp(−⅟₄Δrᵀ(Va+Vb)⁻¹Δr)`（实中心；复数中心留 B7）。
- 去 B4 等 V `ValueError`。等 V 精确退化 = 现 B4 内核（B4 测试不破）。
- GKP QEC 的 loss 后 data V ≠ gkp0 V，fidelity 真实反映有损纠错衰减。

### R4. Fidelity sweep（Q4 锁，A 项）

- 每 γ 点**固定 seed** 跑完整链（`rng=default_rng(seed)`，align Fock F7 确定性），fidelity(final_data, gkp0)。
- GUI `rounds=N` 多 seed 平均选项（教学"平均纠错性能"）。
- 后端新端点（fidelity sweep 带 RNG，不复用纯函数 `/scan`）。

### R5. Step execution（Q6 锁，C 项）

- `/run` 加 `detail="steps"`：一次返回全部 break-point 中间态摘要 `[{step, op, nmode, meters{purity,mean_photon}, wigner(选定单模)}]` + 最终态。
- 前端步进滑条逐帧看 Wigner 演化（CZ 后 / loss 后 / homodyne 后）。
- 复用 `BosonicCircuit.compile()` 段结构——每 break point = 一步。

### R6. Lab 路由解锁（F7 先例）

- `cvsim/lab/ir.py`：`_load_bosonic` + `BOSONIC_WHITELIST`（mirror Gaussian+Fock 白名单，加 `cz/cx/interferometer/gaussian_channel/measure_threshold`）。
- `cvsim/lab/server.py`：`/run`/`/sample`/`/scan` bosonic 路由 + `run_bosonic_circuit`。
- `run_circuit`（Gaussian 纯函数）不动；bosonic 走独立执行路径（seed 驱动）。

### R7. 前端三件套

- palette whitelist：加 `cz/cx/interferometer/mach_zehnder/gaussian_channel/measure_threshold`（GUI 新砖）。
- 结果面板：Wigner evolution view（复用 `cvsim.wigner.wigner_grid` Bosonic 分支，零新物理）+ fidelity sweep curve + step execution 控制。
- `initial` 卡（mode 后选态源 gkp0/gkp1/真空）。

## Acceptance Criteria

- [ ] **AC1（exit 1）**: GKP QEC 主脚本（gkp0→CZ→loss γ→homodyne→feedforward→fidelity curve）GUI 无手写 Python ≤5 min 搭出跑通。
- [ ] **AC2（exit 2）**: golden fixture——Bosonic JSON → `/run` 匹配等价脚本数值（atol 1e-7）。
- [ ] **AC3（exit 3）**: 旧 Gaussian/Fock JSON 行为不变；`backend` 缺省仍 gaussian；pytest + node suite 绿。
- [ ] **AC4**: IR `initial` roundtrip lossless（`["gkp0","gkp1"]` ↔ from_ir ↔ to_ir）。
- [ ] **AC5**: 双 V fidelity 正确性——等 V 退化 = B4 值；γ=0 时 QEC fidelity ≈ 1（理想纠错）；γ>0 单调降；rounds 平均平滑。
- [ ] **AC6**: step execution 中间态摘要逐步正确（CZ 后 nmode=2、loss 后、homodyne 后 nmode=1、feedforward 后）。

## Non-goals

- Gaussian/Fock JSON schema 零改动（`initial` 仅 bosonic 路径消费）。
- 不做 Bosonic unconditional measurement-average（Q4 C 项否决）。
- 不做参数化 initial 态（coherent/cat 带 α——B 项否决，留后续）。
- 不做 complex-center 双 V overlap（留 B7 bridges）。
- 不做 Kerr/协议库（P1 锁）。

## Notes

- K=1 恒定锁保持：initial 之上 gate 不增分量——GKP QEC 才跑得动（O(K·m²)）。
- 单任务拓扑（Q7 锁，align B5/F7 先例）；implement.md 三段（后端→前端→端到端）各自验证。
- Lab import bosonic 边界解锁 = F7 Fock 先例（vision §6.2 更新同步）。
