# Design — circuit_v1 核心 IR 收编

## 0. 语义统一（v0 → v1 关键差异，golden 测试须注意）

| 语义 | v0（Lab 引擎） | v1（核心语义，ADR-0003 #5） |
|------|----------------|------------------------------|
| 模式索引 | 物理索引（heterodyne 删模后直接在收缩态上按原数操作） | **逻辑索引**（compile.py 式静态映射：删模标记 -1、更高逻辑模号下移；引用已删模报错） |
| homodyne | 不删模（mean 路径记录边均值） | **删模**（与 GaussianCircuit/vision §4.4「测后是否删模跟模拟器电路一致」对齐） |
| heterodyne | 删模 | 删模（不变） |

**决策**：v1 引擎采用核心语义（逻辑索引 + 双测删模）。v0→v1 翻译 golden 等价测试只覆盖语义重叠区（heterodyne 后无高模引用、homodyne 在末尾或其后无高模门）；语义统一本身作为 v0 的 bug 修复记录于实现注释。这是 PRD「翻译后与 v0 引擎一致」的收窄，已获用户确认方向（Q6 数组序确认时一并说明）。

## 1. 核心新模块 `cvsim/gaussian/ir.py`

```
SCHEMA = "circuit_v1"
OP_META: dict[str, OpMeta]   # op → {arity, defaults, value_kind, string_params}
OpMeta.arity: 1 | 2 | "all" | "any"
  - 1/2: 固定模式数（squeeze/displace/phase/fourier/loss/amplifier?/homodyne/heterodyne/bs/tms/cz/cx/mach_zehnder/mz）
  - "all": interferometer（modes 必须 == list(range(nmode))）
  - "any": amplifier/phase_noise/gaussian_channel（modes 可为 [] = 全模；builder 语义 mode=None）
OpMeta.value_kind: 每参数名 → num | complex | matrix | str
  - alpha → complex（裸 number 也接受 = 实部）
  - U/X/Y/d → matrix（嵌套数字列表）
  - name → str（measure 名称，fixed string）
  - 其余（r/phi/theta/T/G/nbar/sigma/weight/gain）→ num
OpMeta.defaults: 省略参数 = 库默认（对齐 builder 签名）
```

值编码（JSON 原生，Q3 决策）：

| Python | JSON |
|--------|------|
| `float/int` | 裸 number |
| `complex` | `[re, im]` |
| `np.ndarray` | 嵌套数字列表 |
| 符号参数 `str` | `{"$param": "θ"}` |
| `ParamRef(source, gain)` | `{"$ref": "m_x", "gain": 0.5}` |
| fixed str（`name`） | 裸 string |

顶层：`schema`（必填 == "circuit_v1"）、`nmode`（int ≥1）、`ops`（非空列表）；
扩展字段白名单：`view`/`seed`/`ui`（校验时**忽略**内容，仅类型浅查）；其余未知顶层字段**拒绝**。

`IRNode(id?, op, params, modes)`；`CircuitV1(schema, nmode, ops)`。
`id` 可选：省略不生成（核心不依赖）；存在则必须非空字符串且全局唯一。

`validate_ir(data) -> CircuitV1`：结构校验 only（类型/字段/arity/modes 非负 int/参数 kind）；
**不做**物理范围校验（T∈[0,1] 等留库函数，复用 Lab 现模式，error-handling spec）。

`to_ir(circuit: GaussianCircuit) -> dict` / `from_ir(data: dict) -> GaussianCircuit`：
- `_ops` 五元组 (op, modes, fixed, params, refs) 双向映射；params(符号) → `$param`，refs → `$ref`，fixed → 裸值。
- `from_ir` 按序调 builder；`mz` 展开为 `beamsplitter(θ)→phase(φ,m0)→beamsplitter(θ)` 三步（语义无损，结构性不往返）。
- 往返验收：`from_ir(to_ir(c))` 与 `c` 的 `V,rbar` 一致 atol=1e-12（PRD）。

## 2. `cvsim/gaussian/circuit.py`

- `squeeze(mode, r=0.0, phi=0.0)` 补 phi 参数（vision F-GATE-SET 本就含 phi；builder 缺口，v1 需要）。
- `to_ir()` 实例方法 / `from_ir()` 类方法（委托 ir.py）。

## 3. `cvsim/lab/ir.py` 改造（v1 引擎 + v0 翻译层）

- 保留 `CircuitV0Error(ValueError)` 类名（error-handling spec：FastAPI 422 映射不变量）。
- **`translate_v0(data) -> dict`**（纯函数，v0 JSON → v1 dict）：
  - `nmode` = Σ 源贡献（vacuum nmode 参数 / tmsv 2 / coherent 1）。
  - 源 → 块局部 op：coherent → `displace(alpha, offset)`；tmsv → `two_mode_squeeze(r, offset, offset+1)`；vacuum → 只贡献模数。offset 按序累加。
    （多源 = 真空全空间 + 块局部门顺序应用，与 product 精确等价——Gaussian 不重叠模算子可交换。）
  - 门：单模 `mode` → `modes:[m]`；双模 `modes` 原样；`mz` 保留 op 名（lab 复合 op）。
  - 测：homodyne（phi/name）/ heterodyne 原样；`id` 保留。
  - `view/seed/ui` 复制为扩展字段；`edges` 丢弃（v0 已忽略）。
  - `seed` 提为顶层扩展字段（v1 核心无 seed）。
- **`load_circuit(data)`**：按 schema 分派 —— v0 → translate → validate_ir；v1 → validate_ir。返回 `LabCircuit(core: CircuitV1, seed, view, ui)`。
- **`LabCircuit`**：lab 包装（seed/view/ui 是 UI 概念，不进核心 dataclass）。
- **引擎**：`run_circuit/sample_circuit/scan_circuit` 改为遍历 `CircuitV1.ops`：
  - **逻辑→物理映射**：静态模拟（仿 compile.py `_compile_segments` L112-161）：测删模标记 -1、更高逻辑模号下移；引用已删模 → `CircuitV0Error`。
  - mean 路径（rng=None）：homodyne 记录 `homodyne_mean` 并**删模**（语义统一，§0）；heterodyne 均值 + condition + 删模。sample 路径：真抽样 + condition。
  - 门应用仍走公开 `cvsim.gaussian` API（不复制物理公式，ADR-0003 后果 + ADR-0001）。
- **白名单**：`LAB_WHITELIST` = v1 op 子集（displace/phase/squeeze/fourier/loss/amplifier/beamsplitter/two_mode_squeeze/mz/homodyne/heterodyne，11 op）。lab `load_circuit` 在 v1 校验后追加 lab 白名单拒绝（cz/cx/interferometer/phase_noise/gaussian_channel/mach_zehnder → 422；核心 IR 合法但 Lab UI 未解锁，lab vision §4）。
- `SWEEPABLE_PARAMS` 保留（UI 概念，参数名不变：mz 仍 theta/phi）。

## 4. `cvsim/lab/server.py`

- 零改动预期：`load_circuit` 返回 LabCircuit 后，`run/sample/scan` 取 `.core`/`.seed`/`.view`。
- `_payload` 的 `circuit.seed` → `circuit.seed`（LabCircuit 直接有）。

## 5. 前端（static/ops.js + app.js + staff.js/editor.js）

- 新增 `toV1(nodes, view, seed) -> object`（ops.js）：内部源节点模型 → v1 dict（镜像 translate_v0 的源→门逻辑；gate `mode` → `modes:[m]`；mz 保持）。
- **所有 POST /run /sample /scan body 与 Save 文件统一用 `toV1()` 输出**（schema "circuit_v1"）。
- Save：文件名 `circuit_v0.json` → **`circuit_v1.json`**；`schema: "circuit_v0"` 常量 → `"circuit_v1"`。
- Load：文件内容 v0 或 v1 均可（后端 load_circuit 归一化）；前端加载后仍还原为内部源节点模型（v0 语义不变）。
- UI 状态模型（源节点 + source-first 顺序）保持不变——UI 模型 ≠ 文件格式。
- 前端 `toV1` 与后端 `translate_v0` 的源→门规则重复 ~20 行（JS 无共享，node 测试 + backend golden 双守）。

## 6. 测试

| 文件 | 内容 |
|------|------|
| `tests/test_ir.py`（新） | 14 builder op 往返（含符号参数/ParamRef/复数 alpha/矩阵 U,X,Y,d）；mz from_ir 展开；校验拒绝矩阵（未知 op/坏 modes/重复 id/未知顶层字段/坏参数 kind）；扩展字段忽略；V,rbar atol=1e-12 |
| `tests/test_ir_translate.py`（新） | v0 fixtures（TMSV+loss+bs+heterodyne 主剧本、多源、coherent 源、homodyne 末尾）→ translate → 结构与 V,rbar 对照（主剧本 log_neg = 2r/ln2 等解析值）；语义统一用例（heterodyne 后高模引用、homodyne 删模） |
| `tests/test_*lab*` 存量 | load_circuit/run_circuit 接口形状机械更新（Node → CircuitV1）；语义不变用例保持绿 |
| node 测试 | toV1 emit 结构 + save 文件名 + 旧 v0 文件 load 路径 |

## 7. 文档同步（implement 内做）

- `docs/api-stability.md`：新增 `to_ir/from_ir` + `circuit_v1` IR 为稳定 API（§5 表单）。
- vision 两份已修订（1689d58）；本任务实现中不再改。
