# Bosonic B2：实施计划

## 前置规范

- 目标包：`cvsim/bosonic`；遵守 `.trellis/spec/cvsim/index.md` 与 `.trellis/spec/cvsim/bosonic.md`。
- 物理语义事实源：`docs/vision-bosonic-simulator.md`、`docs/adr/0005-bosonic-production-vision.md`、`docs/adr/0006-bosonic-architecture.md`。
- 共享约定：xxpp、ħ=1、float64、复数 `rbar/w`，不得静默丢弃虚部。
- 只用现有 numpy/scipy；不增加依赖。

## 执行步骤

### 1. B2.1：状态不变量与报告

文件：

- 新建 `cvsim/bosonic/component_eng.py`
- 新建/补充 `tests/test_bosonic_component_eng.py`

内容：

- `LeakReport(frozen=True)`；
- 私有有限性校验；
- `normalize()`；
- `is_hermitian()`；
- 实权重、复共轭权重、零和、空状态、NaN/Inf 测试。

验证：

```powershell
.venv\\Scripts\\python.exe -m pytest tests/test_bosonic_component_eng.py -q
```

### 2. B2.2：稳定组件合并

同一模块追加：

- `merge()`；
- allclose 容差；
- 稳定贪心分组；
- 代表值与复权重求和；
- `merge_distortion` 计算。

补充测试：等价/近邻、链式接近、输入顺序、无合并、畸变和权重守恒。

### 3. B2.3：组件截断

同一模块追加：

- `truncate()`；
- 参数合法性与有限性校验；
- 严格小于阈值删除；
- dropped mass 报告；
- warning/validate/fail 三路行为；
- 全量截断空状态边界。

补充测试：阈值相等、零阈值、NaN/Inf、非法阈值、警告与异常。

### 4. B2.4：集成与收口

文件：

- `cvsim/bosonic/__init__.py`
- `tests/test_public_api.py`
- `pyproject.toml`
- `.trellis/spec/cvsim/bosonic.md` 或必要的 vision 文档

内容：

- 顶层 re-export 五个 B2 名称；
- 更新 `BOSONIC_PUBLIC`；
- 注册 `phaseB2` marker；
- B2 测试添加 marker；
- 最小文档同步，不改变 B3/B4 范围。

验证：

```powershell
.venv\\Scripts\\python.exe -m pytest tests/test_bosonic_component_eng.py tests/test_public_api.py -q
.venv\\Scripts\\python.exe -m pytest -q
.venv\\Scripts\\python.exe -m ruff check cvsim/bosonic tests/test_bosonic_component_eng.py
.venv\\Scripts\\python.exe -m mypy cvsim/bosonic
```

## 完成判据

- 四个子任务 PRD 验收项全部完成；
- B1 与全套回归通过；
- 没有隐式改变现有门、通道、测量行为；
- 公共面冻结测试通过；
- B2 残余边界明确记录：B3 精确测量、B4 对账、B5 DSL 尚未开始。
