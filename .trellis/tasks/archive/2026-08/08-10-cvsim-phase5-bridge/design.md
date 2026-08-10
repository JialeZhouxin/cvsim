# Phase 5 design — Bridges & CV error-correction

## 1. 模块布局

```
cvsim/
├── bridge.py            # 新增：顶层观测值桥（纯函数，无状态）
├── gaussian/
│   ├── observables.py   # + p_click / sample_threshold（outcome-only）
│   └── circuit.py       # + measure_threshold builder（ParamRef 源）
tutorials/
├── _build_06.py         # 新增
└── 06_gkp_feedforward.ipynb
tests/
├── test_bridge.py           # child 1
├── test_threshold.py        # child 2
├── test_gkp_tutorial.py     # child 3（教程自检回归）
└── test_bosonic_consistency.py  # child 4
```

ADR-0001 检查：bridge.py 顶层（跨表示，不属任何 rep 包）；threshold 在 gaussian 包内只依赖 conventions/symplectic + 私有复用 bridge 数学（不进 import —— 用内部实现或单点 import cvsim.bridge？→ **设计决策**：gaussian 包 allowlist 只有 conventions+symplectic，bridge 导入会被 test_architecture 拦。解：vacuum_probability 解析式**内联**到 observables.py（公式短：1/√det 形式），bridge.py 与 observables.py 各自持有公式（注释互链 + 数值互测保证一致）。或者把 vacuum_probability 放 conventions？不 —— 放 observables 私有 `_vacuum_probability`，bridge 公开版也实现同一公式，两边用同一个测试对照。）

## 2. F-BRIDGE 数学（child 1）

| 函数 | 公式 | 测试锚点 |
|------|------|---------|
| `coherent_element(n, alpha)` | ⟨n\|α⟩ = e^{−\|α\|²/2} αⁿ/√n! | FockState.coherent 振幅逐 n 对照 |
| `squeezed_element(n, r, phi)` | ⟨n\|ζ⟩ = (√tanh r)ⁿ √(n!/2ⁿ)/√cosh r · e^{inφ} 修正（n 偶） | FockState.squeezed 振幅对照 |
| `thermal_diag(n, nbar)` | n̄ⁿ/(n̄+1)^{n+1} | FockDensity thermal 对角对照 |
| `vacuum_probability(V, rbar, mode)` | 高斯真空概率闭式（对 mode 约化后 det 公式） | Fock 截断 ⟨0\|ρ\|0⟩ 数值收敛对照 |
| `fock_state_amplitude(n, state)` | FockState 取振幅（对照用） | — |

- 符号约定：α 位移复数（√2 缩放对齐 conventions displace）、r 挤压参数、phi 挤压角（与 S_squeeze 一致）
- FockState 现有工厂名核对（child 1 开工时查 `cvsim/fock/` 工厂 API）
- 数值：float64；对照 atol=1e-10（截断内）

## 3. Threshold outcome-only（child 2）

- `observables.p_click(state, mode)`：1 − 真空概率（约化到 mode 后，高斯解析）
- `observables.sample_threshold(state, mode, rng)`：`rng.random() < p_click` → bool
- `circuit.GaussianCircuit.measure_threshold(mode, name=None)`：记录 op `measure_threshold`，outcome 存 values[name]（0/1），可被后续 ParamRef 引用
- compile.py：measure_threshold 与 homodyne 同路径（outcome 数字入 values，段断点）
- 校验：输入必须 GaussianState；mode 越界 IndexError

## 4. GKP 教程（child 3）

结构（6 节，风格对齐 05）：
1. GKP 思想：多峰逻辑态 → 强挤压 Gaussian 近似（诚实标注）
2. 电路搭建：GKP(ancilla 强挤压) + CZ(data, ancilla) + homodyne(ancilla, p) —— data 位移误差 → ancilla 读出偏移
3. ParamRef：`c.displace(0, alpha=ParamRef('m_p', gain))` 反馈修正
4. 编译 run(values)：数值闭环 + 修正前后保真/方差对照
5. 位移误差扫描：注入 ε 误差 → 检测值线性响应 → 修正残差
6. 小结 + 局限（理想 GKP 需 Bosonic 多峰）

自检断言：误差注入 ε 时读出 ≈ 2ε（或标定增益），修正后 data 方差显著下降。

## 5. Bosonic consistency（child 4）

- `tests/test_bosonic_consistency.py`：
  - 合同固化：vacuum 单分量 / 加权矩公式 / loss w 不变 / 单分量 == Gaussian
  - 桥锚定：cat（偶/奇）⟨x⟩、Var；GKP 多峰 ⟨x⟩、Var —— 解析（桥公式）vs Bosonic 加权矩 vs Fock 截断数值，三向一致
- cat 矩解析：⟨x⟩=0（偶/奇对称）；Var = 1/2 + 2α²·(交叉项因子) —— 推导以现有 Bosonic 矩实现为准（先固化现有实现值，再对桥）
- GKP 峰：⟨x⟩=0、Var≈1/2+小项（多峰平均），以 Fock 截断为参照（GKP 教程里也用到）

## 6. 兼容性与回滚

- 全新增文件 + gaussian 包 2 文件追加函数：零破坏面
- 每 child 独立 commit，可单独 revert
- pyproject 不变（无新依赖）
