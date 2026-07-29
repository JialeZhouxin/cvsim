# Phase 1 退出 demo: 4模TMSV+干涉+loss+homodyne

## Goal

把 Phase 1 五个 P0 Feature（F-STATE-FACTORY、F-SYMPLECTIC-CORE、F-GATE-SET、F-INTERFEROMETER、F-CHANNEL-GENERAL）串成**一条可跑的 4 模态流水线**，跑出的正交观测量数值与**纸笔手算**严格对账（atol=1e-12），作为 Phase 1 整体联动正确性的可复盘证据，正式关闭 Phase 1。本 demo **不引入任何新物理 API**。

## Background

- 愿景 §5 Phase 1 退出共 5 条标准。第 1/2/4/5 条（API 公开、单测、pytest 绿、docstring）已由五个归档切片各自满足；**仅第 3 条未做**："tutorial or demo: interferometer + loss channel + homodyne"。
- 记忆 `cvsim-next-deepen` 标 active = Phase1 exit demo/tutorial，circuit channel hooks `a060b2a` 已完成，本 demo 是接续动作。
- 现有 `tutorials/01_gaussian_beginner.ipynb` §5a 已讲透**单对** TMSV（$m=2$，EPR 关联方差 $e^{-2r}$）。本 demo 是其多模扩展版（$m=4$ 两对 + 干涉 + loss + homodyne）。

## Confirmed facts (from codebase inspection)

- `GaussianState.tmsv(r, nmode=2, mode1=0, mode2=1)` 存在 (`cvsim/gaussian/state.py:131`)。仅 `r` 参数，无 phi（F-GATE-SET 的 phi-squeeze 在单模 `squeezed`，非 tmsv）。
- `GaussianState.product(*states)` 存在 (`state.py:150`)——可用 `product(tmsv_a, tmsv_b)` 拼 4 模。
- `interferometer(state, U, *, validate_u=True)` / 别名 `apply_interferometer` 存在 (`gates.py:160`)；`validate_u=True` 拒非酉。
- `loss(state, T, nbar=0.0, modes=None)` 存在 (`channels.py:118`)；`modes=None` ⇒ 全模。
- `homodyne_mean / homodyne_var / homodyne_sample / homodyne_condition` 存在 (`observables.py`)；$\phi=0$ 测 $x$，$\phi=\pi/2$ 测 $p$。
- 4 模 comp 量来源已有 `test_interferometer.py` 单测（Homomorphism、TMSV+BS、Haar-U）——这些是**单模块**验；demo 需要的是**跨链**多步叠加对账。

## Requirements

1. **源**：两对 TMSV，同压缩量 $r_1=r_2=r=0.6$（与教程 §5a 一致）。mode0,1 = TMSV pair A；mode2,3 = TMSV pair B。用 `GaussianState.tmsv` 与 `product` 组装 4 模初态。
2. **干涉仪**：非平凡酉 $U$ = 50:50 BS 把 mode0↔mode2 混一次。$U$ 用 4×4 酉通过 `interferometer(state, U)` 作用。构造 $U$ 限于 `S_from_unitary` 接受的、可手算的 BS 酉（即可写为恒等外加 BS 子块的酉）。
3. **通道**：loss 透射 $T$（取 $T=0.8$），见 §Technical Notes 取值理由。对**全模** `loss(state, T=0.8, nbar=0.0)` 独立同分布衰减。
4. **观测**：Homodyne **方差**对账。$\phi=0$ 测 $x$ 正交。对账项至少含：
   - 单模 $x_k$ 方差（$k=0,1,2,3$）；
   - EPR 关联方差 $\mathrm{Var}(x_a - x_b)$ 至少一对（首选跨 BS 后仍可手算的对称组合）。
5. **对账**：sim 数值 vs 纸笔手算解析式，`np.allclose(sim, analytic, atol=1e-12)`。
6. **无新 API**：仅调 Phase 1 已公开的 factory/gates/channels/observables；不动 cvsim 源码。
7. **失败行为**：sim vs analytic 不过 atol 时，先打印完整对比表（每项 analytic / sim / diff / 是否过 atol），再 raise。成功路径零输出。
8. **成功路径**：以 `assert np.allclose(..., atol=1e-12)` 收尾；脚本退出码 0 = Phase 1 退出 demo 通过。
9. **可执行性**：仓库无 venv，脚本须能 `py -3 examples/phase1_exit_demo.py` 直接跑（仅依赖 numpy + cvsim 入门 site）。

## Acceptance Criteria

- [ ] `examples/phase1_exit_demo.py` 落盘。
- [ ] `py -3 examples/phase1_exit_demo.py` 退出码 0，所有对账项过 `atol=1e-12`。
- [ ] 脚本含手算公式注释（每对账项标注 analytic 表达式来源）。
- [ ] pytest 全绿（Phase 1 退出第 4 条；需先建 uv venv）。
- [ ] 愿景 `docs/vision-gaussian-simulator.md` §5 Phase 1 退出五条全部勾选（或文档落 `docs/` 一份 Phase 1-exit demo 手算记录）。

## Technical Notes

- **TMSV 方差（无 loss、无 BS 时）**：单模 $x_k$ 方差 $=\frac12\cosh 2r$；EPR 关联 $\mathrm{Var}(x_0-x_1)=e^{-2r}=e^{-1.2}\approx0.3010$（$r=0.6$）。
- **50:50 BS 后**：混合 mode0,mode2 两路 $x$ 输入，输出两侧方差线性叠加（BS 是幺正，保 $\det V$；两边 symmetrize 后方差取均值）。
- **loss 后**：每模 $x_k$ 方差 $\leftarrow T\cdot(\text{loss 前方差})+(1-T)\cdot\frac12$；EPR 关联方差 $\leftarrow T\cdot(\text{loss 前关联方差})+2\cdot\frac{1-T}{2}\cdot\frac12$（两个独立模各拉一份真空噪声）。
- **取 $T=0.8$**：避开 $T=1$（loss 恒等，链路面目退半）与 $T=0$（全真空，信息全失）。$0.8$ 让 loss 真出力、噪声塞得可见、手算非平凡且闭合。
- **取 $r=0.6$**：与教程 §5a 同值，读者对读一致；$e^{-1.2}$ 数值圆润可手抄。
- BS 酉 $U$ 取值固定（避免随机），手算可写。具体 $U$ 构造见 `design.md`。

## Out of scope

- 不加新物理 API。
- 不做 SF / Walrus 对比（Phase 3）。
- 不做 GKP 纠错演示（Phase 5）。
- 不做 $m=100$ 规模基准（Phase 3 F-PERF）。
- 不写 notebook 版本（Q4 已定脚本；notebook 留待 Phase 2）/不接 CI（无 CI）。
