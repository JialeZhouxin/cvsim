# PRD: 教程 GaussianCircuit L3+L4 示例

## 背景

GaussianCircuit 已支持 L3(组合)、L4(测量+前馈)。教程需跟进，展示"为什么这比手动循环好"。

## 新增节

### §5c: 参数化电路扫描（L2+L3）

**目标**：用户学会用 `GaussianCircuit` 做参数扫描，理解与手动循环的区别。

| Cell | 类型 | 内容 |
|------|------|------|
| BOOT | code | 导入（已有，复用） |
| 5c-1 | markdown | 介绍电路范式："定义一次，运行多次" |
| 5c-2 | code | 定义电路 + 扫 CZ weight → 画光子数曲线 |
| 5c-3 | markdown | 对比旧方式（手动 for+reassign），强调"结构=参数分离" |
| 5c-4 | code | `c1 + c2` 组合 + `repr` 查看门序列 |

### §5d: 测量与前馈（L4）

**目标**：用户理解 Homodyne 测量 + 前馈位移，看到迷你 GKP 纠错。

| Cell | 类型 | 内容 |
|------|------|------|
| 5d-1 | markdown | 介绍测量模型：采样→投影→mode消除，前馈概念 |
| 5d-2 | code | 单测量：squeeze→measure，验证 nmode-1、结果存 dict |
| 5d-3 | code | 迷你 GKP: squeeze→CZ→measure p→ParamRef displace，对比反馈开/关 |
| 5d-4 | markdown | 解读:GKP 纠错核心思想(纠缠→测 ancilla→根据结果平移数据模) |
| 5d-5 | code | 两步测量（三模→一模），展示多步前馈 |

### §6 API 速查表 补

| 位置 | 补充 |
|------|------|
| API 速查 → State | 加 `remove_mode` |
| API 速查 → Circuit | 新行：`GaussianCircuit` / `ParamRef` / `measure_homodyne` |

## 约束

- 修改 `tutorials/_build_notebooks.py`，不手改 `.ipynb`
- 中文 markdown，代码注释中文
- 不改动已发布的 §1-§5b cell
- 诚实标注 L5 未做

## 验收标准

1. `python tutorials/_build_notebooks.py` 成功生成 `.ipynb`
2. 在 Jupyter 中 Restart & Run All 无报错
3. 5c 扫图 cell 输出 CZ weight→光子数曲线
4. 5d 迷你 GKP cell 输出反馈开/关的均值对比
5. API 速查表含 `GaussianCircuit`/`ParamRef`/`measure_homodyne`
