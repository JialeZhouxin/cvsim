# Bosonic B2：组件工程设计

## 1. 目标与边界

B2 只建立组件管理基础设施，不改变 B1 门、通道、测量的现有语义。所有组件工程操作都是显式纯函数；输入 `BosonicState` 不就地修改。

实现集中于：

```text
cvsim/bosonic/component_eng.py
```

测试集中于：

```text
tests/test_bosonic_component_eng.py
```

顶层导出和阶段冻结放在 B2.4 处理。

## 2. 数据与不变量

沿用 `Component(V, rbar, w)` 和 `BosonicState(components)`，不新增状态层级或张量结构。

- `V` 为 float 数组，`rbar` 为 complex 数组，`w` 为 complex。
- 所有入口先检查 `w` 是否 finite；NaN/Inf 直接 `ValueError`。
- 归一化判据始终是 `sum(w) == 1`（在容差内），不能使用 `sum(abs(w))`。
- 空状态的 `weight_sum` 为 0；`normalize(empty)` 因零权重和抛 `ValueError`。

## 3. LeakReport

使用不可变 dataclass：

```python
@dataclass(frozen=True)
class LeakReport:
    input_components: int = 0
    output_components: int = 0
    dropped_components: int = 0
    dropped_weight_mass: float = 0.0
    merge_groups: int = 0
    merge_distortion: float = 0.0
    warning: bool = False
```

`dropped_weight_mass` 定义为被删除组件的 `sum(abs(w))`，只作为质量预算；它不参与状态归一化。

## 4. normalize

```python
normalize(state, *, atol=1e-12) -> BosonicState
```

计算 `s = weight_sum(state)`，若 `abs(s) <= atol` 抛 `ValueError`；否则复制每个组件，仅将 `w` 替换为 `w / s`。`V/rbar` 拷贝保持不变。归一化不修复厄米性。

## 5. is_hermitian

```python
is_hermitian(state, *, atol=1e-10, rtol=1e-8) -> bool
```

对每个组件寻找一个尚未要求唯一消费的候选配对：`V` 用 `allclose`，`rbar` 用 `allclose(conj(...))`，`w` 用 `allclose(conj(...))`。实组件可与自身匹配。该校验只返回布尔值，不修改状态、不自动补项。

## 6. merge

```python
merge(state, *, atol=1e-10, rtol=1e-8) -> tuple[BosonicState, LeakReport]
```

使用输入顺序稳定贪心分组：

1. 取第一个未处理组件为组代表；
2. 后续组件只与该代表比较 `V` 和 `rbar`；
3. 都满足 `np.allclose` 则加入当前组；
4. 代表保留第一项的 `V/rbar`；权重求和；
5. 继续处理下一个未处理组件。

报告：`merge_groups` 为输出组中实际合并的组数（组大小大于 1）；`merge_distortion` 为所有成员相对组代表的 `V/rbar` 元素绝对差最大值；无合并则为 `0.0`。合并不检查或改变归一化。

## 7. truncate

```python
truncate(
    state,
    *,
    amp_cutoff=1e-6,
    validate=False,
    warn_threshold=1e-6,
    fail_threshold=1e-3,
) -> tuple[BosonicState, LeakReport]
```

- 参数必须 finite；`amp_cutoff`、阈值必须非负。
- 保留 `abs(w) >= amp_cutoff`，删除严格小于阈值者。
- `dropped_weight_mass = sum(abs(w))`。
- 质量 `> fail_threshold` 或 `validate=True` 且质量 `> warn_threshold`：`ValueError`。
- 质量 `> warn_threshold` 且未失败：`RuntimeWarning`，报告 `warning=True`。
- 删除全部组件且未触发失败时返回空状态。
- 不自动归一化。

## 8. 执行与验证顺序

1. B2.1 实现状态不变量与报告，运行专项测试。
2. B2.2 在同一模块追加 merge，运行专项测试。
3. B2.3 追加 truncate 与阈值纪律，运行专项测试。
4. B2.4 处理导出、公共面、marker、文档，运行 B1+B2+全套 pytest；再运行 ruff/mypy。

B2 不引入新依赖，不修改共享电路框架，不接入门/通道/测量隐式调用。
