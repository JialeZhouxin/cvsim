# ADR-0010: Lab 执行分派单点（dispatch）

- 日期: 2026-09-07
- 状态: 已接受
- 来源: /improve-codebase-architecture 候选 1 → /grill-with-docs 拷问定案

## 背景

ADR-0008 统一了**响应**规约（LabResult + serialize 单点），但**到达它的路**未统一：
backend 分派散在 `server.py` 7 处 `backend ==` 判断；gaussian 执行体 `_execute` 住在
`ir.py`（经 D1-A 函数内 import 调 gaussian_backend._build_result，规避循环导入）；
`/run` `/sample` 共 5 处手造 `np.random.default_rng(circuit.seed)`；`detail=steps`
是 server `body.pop` 的无名旁路参数。新表示接入者必须读懂 server 分派 + ir.py 执行体
才能知道第四个 runner 藏在哪。架构评审（2026-09-07）定为最强深化候选。

## 决策

1. **新建 `cvsim/lab/dispatch.py`**：`/run` `/sample` 的唯一执行入口，按
   `LabCircuit.backend` 路由到三表示 runner（runner 注册表，一行一后端）。
2. **双动词 interface 不变**：`run_circuit(circuit)` / `sample_circuit(circuit, rng=None)`
   保留现名，实现移居 dispatch.py。`rng=None` 时 dispatch 内部
   `default_rng(circuit.seed)` 派生——server 的 4 处 rng 构造收单点。
   深化 = interface 不变、实现变深；改名（`run_result(backend, …)`）被否：
   backend 已在 LabCircuit 上，单独传参冗余，且砸掉 cvsim.lab 顶层动词调用面。
3. **`_execute` 搬进 `gaussian_backend.py`**：三个表示的 runner 形状对齐
   （执行 + 组装同文件）；D1-A 循环导入 hack 消灭，ir.py 退到 load/translate/schema。
4. **`detail=steps` 升格为 LabCircuit 扩展字段**：`load_circuit` 解析（str|None），
   bosonic runner 自读 `circuit.detail`。字段名共享、语义按后端二分（学 initial），
   不再是绕过 load/schema 的旁路；`/run` 路由收成两行。
5. **view 守卫模板单点、兜底差异声明不统一**：`check_wigner_mode(wmode, nmode)`
   收消息模板；三表示 wigner 失败兜底语义不同（gaussian → singular=True、
   bosonic → 每步 None、fock → raise）是物理事实，docstring 声明，学 meter 支持矩阵
   「差异是物理事实，永不 paper over」。
6. **422 错误元组提为单点常量**（`DOMAIN_ERRORS`），每路由 except 照旧两行；
   route-wrapper 装饰器被否：golden 422 文本路径变绕，两行重复的税更便宜。
7. **/batch /scan /fidelity 门禁不动**：曲线形端点已由 ADR-0008 决策 5 排除在
   LabResult 契约外，单生产者无镜像，显式拒绝即诚实形状；能力矩阵是 YAGNI。
8. **守卫换防**：删 `test_gaussian_backend_has_circuitv0error`（对象消失）；
   换两个 AST 结构守卫——server.py 不得 import 任何 runner 模块（只经 dispatch）；
   ir.py 不得含 gaussian 执行知识（GaussianState / _apply_measure）。
   golden 响应、meter 矩阵守卫、cvsim.lab 顶层动词 re-export 原样存活。

## 权衡

- **dispatch.py vs runners.py vs 塞进 result.py**：result.py 章程是「只管响应侧」
  （模块 docstring 明言），塞执行破坏它；dispatch 命名直指职责（分派，不执行物理）。
- **新 ADR vs amend 0008**：0008 已 Accepted 且每条决策原样成立，本决策是它
  请求侧的续篇，不是改写——独立成篇，历史干净。
- **Q4 曾想「wigner 兜底 ×5 收单点」**：核对代码后被事实打脸——守卫只能 post-run
  （删模改变 nmode），兜底语义三表示各异；诚实的深化是模板单点 + 差异声明，
  不是硬统一。

## 后果

- 新表示接入 = 注册表加一行 + 一个 LabResult runner，分派知识零漂移。
- server.py 不再知道任何执行细节；`/run` `/sample` 路由体收敛到 try/load/dispatch/
  serialize 四拍。
- ir.py 职责收窄为「circuit JSON → LabCircuit」（load/translate/view/seed/initial/
  detail 解析），不再 import gaussian 执行符号。
- 术语「Lab 执行分派 (dispatch)」进根 CONTEXT.md。