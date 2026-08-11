# Phase 5 — Bridges & CV error-correction 完成（2026-08-10）

4 child + parent 全归档，0 活跃任务。基线 700 → 758 全绿（+58 测试）。

## C1 F-BRIDGE（commit 762037b + 2 fix）
- `cvsim/bridge.py` 顶层 5 函数：coherent_element / squeezed_element（φ=0 对齐 Fock expm 含 (−1)ᵐ，标准公式 √(2m)!/(2ᵐ·m!)·zᵐ/√cosh r）/ thermal_diag / vacuum_probability（xxpp 单模块闭式 + PSD 检查）/ fock_state_amplitude
- 25 测试；OCR 抓到真 bug：vacuum_probability mode 约化原用 xpxp 切片被自洽测试掩盖 → 改 xxpp 序（fc7c9d7）+ 测试期望修正（54195c2）
- 对照 atol 因 Fock expm 截断泄漏放宽（1e-9/1e-7）并注释

## C2 threshold outcome-only（17a0e9a + 2 fix）
- `p_click`/`sample_threshold`（observables）+ `measure_threshold` builder（不删模）+ compile 断点 + IR 注册（b1ee0ca）+ api-freeze 同步
- OCR 2 medium：IR round-trip 缺失 → 注册；非物理 V 产出负 p_click → p0∉[0,1] 抛 ValueError（882cbc5）
- 17 测试

## C3 GKP 教程（4aca29f，OCR 服务端连续失败 → trellis-check 兜底 amend）
- `tutorials/_build_06.py` + `06_gkp_feedforward.ipynb` 6 节：data x 挤压 + ancilla F·S·F p 挤压 → CZ 传播 → homodyne p 读出 → ParamRef 反馈
- **物理标定**：读出=ε+η（双噪声源 std≈e^{−r}），修正残差=−η_anc（data 噪声自抵消）std≈e^{−r}/√2（实测 0.253/0.153/0.093/0.056 vs 理论 0.260/0.158/0.096/0.058）
- 5 回归测试；trellis-check 修正读出 std 对照（初版误写 e^{−r}/√2）

## C4 Bosonic 一致性（5b672c0）
- 合同固化：vacuum 单分量 / 加权矩公式 / loss 权重不变 / 单分量==Gaussian
- 桥锚定：cat 偶奇 ⟨x̂²⟩=[(1+4α²)±o]/[2(1±o)] 三向（Bosonic==bridge 解析==Fock 截断 40）；gkp0 ⟨x⟩=0 对称、gkp1 ⟨x⟩=√(2π)/2≈1.2533 解析锚
- 9 测试；OCR 服务端失败 → trellis-check 兜底（+4 修：phi=π/2、import 排序、zip strict）

## 收口（69ac65d）
- vision v0.4.0：Phase 5 exit 1/2 ✅ + gap table 4 行 + 版本记录
- CONTEXT.md +3 术语（F-BRIDGE 观测值桥 / threshold 编译语义 / CVCircuit 不泛化已在此前）

## 备注
- OCR 服务端 2026-08-10 后半段持续故障（C3/C4 各 2 次 failed，0 findings）→ trellis-check 兜底（含 ruff/mypy/数学抽查），纪律已执行
- 遗留勿提交：benchmarks/latest.json（Phase 3 产物）
- 提交链：762037b→fc7c9d7→54195c2→17a0e9a→882cbc5→b1ee0ca→4aca29f→5b672c0→69ac65d（+8 archive chore）
