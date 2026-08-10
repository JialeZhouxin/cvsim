# Fock 模拟器愿景（planning 完成，待产出文档）

## Goal

产出 `docs/vision-fock-simulator.md` —— 与高斯模拟器**平级**的生产级 Fock 愿景（单源真理，镜像高斯 vision 结构）。

## 已确认事实（仓库查证 2026-08-10）

- `cvsim/fock/`：FockState（1/2 模截断纯态）/ FockDensity（2 模）/ gates（squeeze/phase/displace/kerr/BS/tms）/ channels（loss 1/2 模 Kraus）/ observables（norm/trace/mean_photon/pnrd_probs/homodyne 族含 condition）/ 19 项导出
- 测试 10 文件；教程 `02_fock_beginner.ipynb`、`03_bosonic_beginner.ipynb`
- `cvsim/bridge.py`：观测值桥（coherent/squeezed/thermal 元素、fock_state_amplitude、threshold p_click）
- 主 vision §6 锁规则："Gauss→Fock 小模公式；Fock→Gauss 仅当高斯容差内否则拒绝；绝不静默截断"；Lab vision 锁 "no Fock GUI"

## 已锁决策（Q1–Q12 用户拍板）

| # | 决策 |
|---|------|
| Q1 | 生产级第一公民，与高斯平级 |
| Q2 | 独立 `docs/vision-fock-simulator.md`，主 vision 链接引用 |
| Q3 | 能力面平级（gates/channels/measures/analyse/DSL+compile/双后端）+ 截断工程横切 |
| Q4 | roadmap 镜像高斯相位结构（F0 baseline → F1 core → F2 analyse+measure → F3 compile+sample+截断 → F4 AD → F5 桥+集成 → F6 interop） |
| Q5 | 共享电路框架（半泛化：op 列表+参数+编译遍历抽公共层，GaussianCircuit/FockCircuit 各自实例化；YAGNI 反转——第二消费者已出现） |
| Q6 | 规模硬锚：稠密 m≤4 保真（cutoff 自适应 20–40）、m=6 上限超限拒绝；稀疏光子数态延伸 m=10+；fail-fast |
| Q7 | 截断纪律：泄漏指标（尾部概率 Σ）量化 + 默认 RuntimeWarning + validate=True 或 >1e-3 时 ValueError |
| Q8 | backend= 双后端 + Fock AD 平级（FD 验证），F4 落地 |
| Q9 | Fock GUI 长期必须 + 与高斯 GUI 兼容性待评估（开放项，前置=模拟器本体 roadmap 完成） |
| Q10 | 教程平级（每 phase 带 Run-All + 数值回归） |
| Q11 | 桥保持 §6 规则 + 观测值桥转正（元素转换 + 观测值传播 + threshold/PNR 桥接，F5） |
| Q12 | 非目标：玻色采样算法竞赛 / 张量网络（远期研究项标注）/ m>10 任意态 / 云+多用户 / Fock GUI（短期） |

## Deliverables

- [ ] `docs/vision-fock-simulator.md`（结构：Purpose & non-goals / Conventions / Architecture / Phased roadmap & exit criteria F0–F6 / 截断工程纪律 / 数值预算 / 与高斯关系 / Testing doctrine / Gap snapshot / Open questions / Document control）
- [ ] 主 vision §6/§10 Fock 行改链接引用
- [ ] CONTEXT.md 术语补充（截断泄漏、稀疏态表示、共享电路框架）
- [ ] 用户审阅定稿 → commit

## Acceptance Criteria

- [ ] 愿景文档覆盖全部 12 项已锁决策，无遗留待问
- [ ] 与高斯 vision 同构（phase 语义/预算/测试 doctrine 对齐）
- [ ] 用户审阅通过
