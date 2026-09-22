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

   > **补记（2026-09-18 审计后修复）**：注册表建起来了，但路由体里还留着
   > **三处 `if circuit.backend == ...`**（`rng` 派生一处、`steps` 转发两处），
   > 于是"一行一后端"对本条决策**部分失效** —— 接第四个后端仍要回来读分派。
   >
   > 现已收口：
   > - **`steps` 两处是纯冗余，已删**。bosonic 的 `run_bosonic_circuit:114`
   >   本来就 `want_steps = steps or circuit.detail == "steps"` —— 即 #4
   >   已经落地，dispatch 再转发一次没有意义；且三个 runner 签名早已统一为
   >   `(circuit, rng, *, sampled, steps)`。
   > - **`rng` 一处改为注册表数据**：行类型从"callable"变成
   >   `_Runner(callable, wants_rng)`。之所以不能简单统一，是因为
   >   `rng=None` 的语义三表示不同 —— gaussian 是"走均值路径"（必须保持
   >   `None`），bosonic 是"没给生成器 → 测量层自造未播种 `default_rng()`"
   >   （必须派生），fock 的测量层同样会自造、但 `run_fock_circuit:152`
   >   自己兜了种子（故 dispatch 派生与否对它行为冗余，标志属防御性声明）。
   >   `wants_rng` 只描述**非采样**路径；`/sample` 下三者都派生。
   >
   > 配套守卫：`test_dispatch.py` 用 AST 断言路由函数体内**零** backend
   > 比较，并加"伪造第四后端只加一行即两动词跑通"的可执行声明。
   > 变异验证：换回 `circuit.backend != "gaussian"` → 红。
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

   > **补记（2026-09-18 审计后修复）**：本条的**落地方式**原与决策文本不符 ——
   > 代码里叫 `_wigner_mode_guard_fail`，**定义在 `fock_backend.py`**，
   > `gaussian_backend.py` 里有**第二份逐字节相同的定义**，`bosonic_backend.py`
   > 则**跨包 import fock 的私名**（这就是被登记的那个例外）。
   > 且函数名说"fail"、函数体却不做判断 —— 五个调用点各自手写 `if mode >= nmode`。
   >
   > 现已按决策文本归位：`cvsim/lab/ir.py` 的 **`check_wigner_mode(mode, nmode)`**
   > 同时持有**模板与比较**，三个 backend 只保留调用点，
   > 跨包 import 与两份重复定义一起消失，`test_lab_backend_symmetry.py` 的
   > 例外开洞同步删除（改为"不得 import fock_backend"的硬断言）。
   > 选 `ir.py` 而非 `result.py` 的理由：`result.py` 的章程是"只管响应侧"且被
   > `test_result_py_dependency_bottom` 锁成"只 import numpy"（见下方权衡），
   > 而 `CircuitV0Error` 与 `View` 都定义在 `ir.py`，三个 backend 本来就 import 它。
   > 仍留在各 backend 的只有**兜底语义**（本条决策后半段）与 bosonic 的
   > `nmode == 0` 前置条件 —— 那两样确实是物理事实。
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