# PRD: Gaussian 电路组合 + 测量前馈 (L3+L4)

## 背景

`GaussianCircuit` L2 已支持参数化 + 固定参数的一键模拟。L3 补电路复用，L4 补测量+前馈，解锁 GKP 纠错教学。

---

## L3: 电路组合

### R3.1: 就地拼接 `+=`
```python
c1 = GaussianCircuit(2); c1.squeeze(0, r=0.5)
c2 = GaussianCircuit(2); c2.cz(0, 1, weight=0.3)
c1 += c2  # c1 尾部追加 c2 的全部门
assert len(c1) == 2
```

### R3.2: `+` 返回新电路
```python
c3 = c1 + c2  # 新电路 = c1门 + c2门，不变动 c1/c2
```

### 语义约束
- `nmode` 必须相同，否则抛 `ValueError("nmode mismatch: 2 vs 3")`
- 参数名冲突：允许重名（不同电路可以有同名参数，由调用者负责传唯一值）

---

## L4: 测量 + 前馈

### 核心想法

把电路执行模型从 `state → state` 升级为 `state → (state, measurements)`：

```python
c = GaussianCircuit(2)
c.squeeze(0, r=0.5)
c.cz(0, 1, weight='g')
c.measure_homodyne(1, phi=np.pi/2, name='m_p')  # 测 mode1 的 p 分量
c.displace(0, alpha=ParamRef('m_p', gain=0.5))    # feedback: alpha = m_p * 0.5

state, results = c.run(g=1.0)
# results == {'m_p': -1.204...}
```

### R4.1: 投影测量 `measure_homodyne`
- `measure_homodyne(mode, phi, name)` — 理想 Homodyne 测量，角度 φ
- 执行时：从当前 state 采样一个 Homodyne 值，将 state 投影到对应本征态
- 返回值记录在 `results[name]` 中
- 测量后 mode 被消除（条件化后的态不再有该 mode 的自由度）

**设计决策 A：测量后的 mode 去哪？** 两种选择：
- **A1（消除）**: state 的 `nmode` 减少 1 — 干净但需处理门索引重映射
- **A2（冻结）**: mode 保留但 V/r̄ 冻结，后续门不能再作用于该 mode

选 A1——消除，物理干净。代价：后续门的 mode 索引需偏移处理。

### R4.2: 参数引用 `ParamRef`
```python
class ParamRef:
    source: str   # 测量名
    gain: float   # 乘因子
```
`displace(mode, alpha=ParamRef('m1', gain=0.5))` → `alpha = results['m1'] * 0.5`

`ParamRef` 对位移有效，以后可扩展到其他门类型。

### R4.3: `run()` 返回类型变化
- 无测量：返回 `GaussianState`（向后兼容）
- 有测量：返回 `tuple[GaussianState, dict[str, float]]`

### R4.4: 多步测量
```python
c.measure_homodyne(0, phi=0, name='m_x')
c.measure_homodyne(1, phi=np.pi/2, name='m_p2')
c.displace(0, alpha=ParamRef('m_x', 0.3))
c.displace(1, alpha=ParamRef('m_p2', -0.3))
```
按序执行，每次测量时 state 有当前时刻的完整模式信息。

---

## 非需求

- 不做前馈判定逻辑（if-else 分支、基于测量结果换不同门序列）
- 不做电路可视化
- 不做模式重映射 DSL（测量消除后手动管理索引）

## 验收标准

1. `c1 + c2` 返回新电路，`c1 += c2` 就地修改
2. `measure_homodyne` 后 state 的 mode 数减 1
3. `ParamRef` 引用已测量值，门参数正确缩放
4. 有测量时 `run()` 返回 `(state, dict)`
5. 简单 GKP 式纠错电路能运行：制备 ancilla → CZ → 测量 → 反馈位移
6. `pytest tests/ -x -q` 全绿
