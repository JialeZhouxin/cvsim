# ADR-0004: 共享电路框架（circuit_common）与 Fock 生产级架构

- 日期: 2026-08-10
- 状态: 已接受（用户 review 通过后生效）
- 前置: ADR-0001（模块边界）、ADR-0002（编译架构）、ADR-0003（circuit_v1 IR）

## 背景

Fock 生产级愿景（`docs/vision-fock-simulator.md`）Q5 锁定：**共享电路框架** ——
GaussianCircuit 与 FockCircuit 共享表示无关的 DSL 核。这反转 Phase 5 的
"CVCircuit 不泛化" YAGNI 决策：第二消费者（Fock 生产级）已真实出现。

现有 `GaussianCircuit`（383 行）+ `compile.py`（374 行）经分析可拆出表示无关部分：
`ParamRef`、`_ops` 5 元组结构、`_partition` 参数分类、`_compile_segments`
分段骨架（segment 划分 + mode-mapping 模拟）、`CompiledGaussian.run` 遍历、
`__iadd__/__add__/__repr__/__len__` 骨架。表示特定部分：`_factor`（S,d 构造）、
`_instantiate`（合并）、`_run_op`/`_DISPATCH`（物理执行）、测量语义、
break/merge 集合。

ADR-0001 限制 `cvsim.fock` 只能 import `conventions` + `symplectic` ——
共享层必须进入 allowlist。

## 决策

### 1. 共享层形态：纯函数工具库 + 注册表（D1, grill 2026-08-10）

`cvsim/circuit_common.py` 单文件（D2，≈280 行）：

- `ParamRef`（从 gaussian.circuit 迁出）
- `partition(op_name, modes, *, _fixed_str_keys, **kwargs)` → 5 元组
  （从 `GaussianCircuit._partition` 迁出）
- `compile_segments(ops, nmode, *, break_ops, remove_mode_ops)` →
  `(segments, params)`：`_compile_segments` 泛化，break/remove 集合参数化
- `CompiledCircuit` 基类：`nmode` / `params` / `run(**values)` 遍历骨架；
  物理执行经注册表注入

每表示提供注册表（frozen dict）：
`FACTOR`（merged 段物理构造）、`DISPATCH`（break 段执行）、
`BREAK_OPS` / `REMOVE_MODE_OPS` 集合、测量语义回调。

不采用继承（b）：383 行高斯代码会躺进继承缝，重构面最大。
不采用 mixin（c）：两个消费者，YAGNI。

### 2. 迁移策略：立即迁移（D3）

提取 = git mv 语义：把高斯代码搬进 `circuit_common.py`，`GaussianCircuit` 改
import 共享层。**不存在双份逻辑**。回归安全网：766 测试（高斯 758 + Fock 8）。
迁移是独立切片（F1 前置或 F3 前置均可；推荐 F1 前置，避免 FockCircuit 建在
未迁移的骨架上）。

### 3. Fock 包模块划分（grill 2026-08-10 用户认可）

```
cvsim/fock/
├── state.py        # FockState + 工厂 + truncation_leakage/check_leakage
├── density.py      # FockDensity + from_pure + thermal 工厂
├── gates.py        # 命名门 + apply_unitary
├── channels.py     # Kraus 通道 + 通用 apply_kraus
├── observables.py  # 期望/测量（homodyne 族现有 + heterodyne/PNR condition F2）
├── analyse.py      # 新建 F2：entropy_vn/log_negativity/fidelity/partial_trace
├── circuit.py      # 新建 F3：FockCircuit（基于 circuit_common）
├── compile.py      # 新建 F3：Fock 编译
└── __init__.py     # 公共导出（F2 冻结 api-freeze）
```

### 4. 接口规格（grill A–H 锁定）

| 模块 | 接口 | 备注 |
|------|------|------|
| state | 标量 `cutoff`（A）；per-mode `cutoffs` 元组 F2/F3 演进，`cutoff` 保持兼容 | 工厂：`coherent(cutoff, alpha)` / `squeezed(cutoff, r, phi=0)` / `cat(cutoff, alpha, even=True)` 类方法；thermal 归 density |
| leakage | `truncation_leakage(state) -> float \| None`（工厂态精确，非工厂态 None）+ `check_leakage(state, *, validate=False, warn_threshold=1e-6, fail_threshold=1e-3)` + `estimate_leakage(state, cutoff2)`（高 cutoff 对照工具，m≤2） | 三件套（B）；未知不误报 |
| gates | F1 新增 `cz/cx(state, weight, m1, m2)`（连续变量物理 e^{i g x̂⊗x̂}，与高斯一致）、`mach_zehnder`、`interferometer(state, U)`（全模式张量积）、`apply_unitary(state, U, modes=None)`（Fock 独有通用入口） | 不引入 qubit 编码门（YAGNI） |
| observables | F2：`pnr_sample/pnr_condition/pnr_sample_and_condition`、`heterodyne_condition/heterodyne_sample_and_condition` | 镜像高斯族命名；不做 heterodyne mean（YAGNI） |
| analyse | F2 镜像 `cvsim/gaussian/analyse.py` 签名 | nats |
| circuit | F3：FockCircuit builder 镜像高斯 + `measure_pnr`；`compile()/run()/to_ir()/from_ir()` 同构 | 测量语义走注册表回调；IR schema 演进 F3 定 |
| api-freeze | F2 出口做 Fock 版 `__all__` 冻结测试 | 镜像高斯 Phase 2 |

### 5. ADR-0001 修订

`cvsim.gaussian/fock/bosonic` allowlist 增加 `cvsim.circuit_common`。
`tests/test_architecture.py` AST 扫描同步。修订在 F3 前置（FockCircuit 需要时），
但设计文档现在生效。

### 6. 截断工程（Q7）落点

泄漏检查挂 state.py（镜像高斯 validate_state 位置）；FockCircuit.run 的检查
策略（编译期 vs 运行期）留 F3 prd。

## 后果

- 正面：一套 DSL/编译骨架，两个消费者；Fock 复用高斯踩过的坑（measurement
  mapping、ParamRef 绑定、segment 划分）
- 负面：高斯重构回归风险 → 766 测试兜底 + 独立迁移切片验证
- 开放：Fock merged 段合并策略（Kronecker 优化）F3 定；IR schema 演进 F3 定；
  双后端 F4 评估 ADR-0001 是否再修订
