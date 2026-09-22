# Review: 模块边界 / 可维护性审计（全项目）

| 字段 | 内容 |
|------|------|
| 审查范围 | 全项目：`cvsim/`（根模块 + 三表示包 + `cvsim/lab/`）、`cvsim/lab/static/`、`tests/`、`tools/`、`scripts/`、`examples/`、`benchmarks/`、`pyproject.toml`、`.github/workflows/ci.yml`、`docs/adr/` |
| 代码基线 | `1e207cd`（2026-09-18，`master`） |
| 审查日期 | 2026-09-18 |
| 方法 | 静态代码审查（模块边界 / 接口深度 / 重复实现 / 死代码 / 契约漂移）+ **实测**（三表示 IR 校验行为对比、函数体逐字比对、AST 扫描、`ruff` / `mypy` / `pytest` / `node --test` 基线复跑） |
| 性质 | **只读分析**起步；审计后已按 §5 顺序落地 **§4.1 / §1.1 / §1.2（值校验部分）**，各项下方标注「已修」并附验证输出 |
| 已改动文件 | `cvsim/circuit_common.py`、`cvsim/gaussian/ir.py`、`cvsim/fock/ir.py`、`cvsim/bosonic/ir.py`、`cvsim/lab/ir.py`、`cvsim/lab/{fock,gaussian,bosonic}_backend.py`、`cvsim/lab/static/{editor,fock,initial}.js`、`tests/test_ir_schema.py`、`tests/test_fock_ir_f3.py`、`tests/test_lab_ui.py`、`tests/test_lab_backend_symmetry.py`、`tests/test_dispatch.py`、`tests/{editor,fock}.test.mjs`、`docs/adr/0010-lab-dispatch.md`、**新增** `tests/test_ir_parity.py`、**新增** `tests/test_frontend_leaf_suite.py`、**新增** `tests/lab_initial_clamp_probe.mjs`、`.github/workflows/ci.yml` |

> ⚠ **下游任务必读 —— 本文会被 Trellis 按字节截断。**
> 本文 **60+ KB**，超过 Trellis 的 `context_injection.max_file_bytes`（32768），
> 下游任务读到的版本会**按字节截断尾部**，且**每次往本文加内容，边界都会往前移** ——
> 不要依赖"某节一定在窗口内"。
> **因此本文把三块最不能丢的内容主动前置**：**§0 优先级总表**、**§5 建议实施顺序**、**§6 基线复现**。
> **当前实测边界**：窗口内 = 文档头 + §0 + §5 + §6 + §1 + §2 + §3 + **§4.1–§4.4**；
> 窗口外 = **§4.6 及之后**（§4.7 / §4.8 / §4.9 / §4.10 / §4.11）。
> ⚠ 这里**故意不写精确字节偏移** —— 本文每改一次它就失效（写这个数字本身就会让数字变化）。
> 要精确边界就**跑 §6 的「复测截断窗口」脚本**，别信文中的数字。
> **注意 §4.6 之后全在窗口外** —— 但这些条目已进 §0 表（带 `file:line` 锚点）。
> **凡下游任务需要的依据，要么前置到本文前三块，要么写进该任务自己的 `prd.md` / `implement.md`。**

**核心结论**：项目自己有一套**成文的边界契约**（ADR-0001 表示包互斥、ADR-0003 circuit_v1、
ADR-0004 共享 DSL 核心、ADR-0008 LabResult、ADR-0009 前端 leaf 测试、ADR-0010 dispatch 单点），
且用 `tests/test_architecture.py` + `tests/test_public_api.py` 做了**零依赖 AST 守卫**。
真正的问题不是"没有架构"，而是**三处**：

1. **合法的镜像没有漂移守卫** —— ADR-0001 逼出三份 `ir.py`/`compile.py` 镜像，这是对的，
   但只守了 arity，**行为已经漂了**。§1.1 实测：fock 的 `validate_ir` 比另两份少 **6 组 23 项**检查，
   其中负模索引会**静默算出错误物理**；✅ 已修，并补上 `tests/test_ir_parity.py` 让镜像从此有守卫。
   ADR-0010 明写的"分派知识零漂移"也在 `dispatch.py` 里被三处 `backend ==` 特判打回原形
   （§2.2）—— ✅ 已修：两处 `steps` 转发是纯冗余（bosonic 自己读 `circuit.detail`）已删，
   rng 差异改为注册表行的 `wants_rng` 标志；路由体零 backend 比较，配 AST 守卫 +
   "伪造第四后端只加一行"的可执行声明。
2. **前端 leaf 纪律半途而废** —— `app.js` 是 0 export 的装配壳（符合纪律），
   但约 330 行本该属于 leaf 的逻辑留在里面，`node --test` 结构上够不到（§3.3）；
   leaf 契约层**原本根本不在 CI 里跑**，✅ §4.2 已补上 `frontend` 任务 + 接线守卫；
   ✅ §3.3 已把那 330 行里**三个零 DOM 纯逻辑段**拆成 leaf（+30 条 node 测试），
   只剩 `heatmap.js`（与七个模块级缓存焊死、被像素哈希探针把守）待做。
3. **契约数据有声明无消费者** —— `LAB_RESULT_CORE_KEYS`（§1.4）、`_MERGEABLE_OPS`（§1.4）、
   `/schema` 的 `extensions.sweepable`（§3.7）三处都是"声明了单点，但没人读"。

---

## §0 优先级总表

> 本表**故意放在最前**：它是窗口内一定可见的部分，也是唯一"按严重度全局排序"的视图。
> 每条的详细证据（`file:line` + 实测）在对应小节；若该节被截断，请按本表的位置锚点直接读源码。

**先看这几条**（§5 前 4 项已全部完成）：

- ✅ **1.1 已修** —— fock `validate_ir` 补齐 **23 项**缺失校验（负模索引原本静默算出错误物理），
  并加了 `tests/test_ir_parity.py` 三表示等价守卫（60 个用例，已做变异测试确认能抓回归）。
- ✅ **1.2 已修（值校验部分）** —— 四个值校验 helper 收进 `cvsim.circuit_common`，
  `_json_defaults` 统一（bosonic 不再往 schema 载荷漏 numpy 对象）。
- ✅ **4.1 已修**（本文档写入后修复）—— CI lint 原本在 `master` 上红，tuple 折行后 `ruff` 全绿。
- ✅ **4.2 已修** —— CI 新增 `frontend` 任务跑 `node --test`（此前 9 个 leaf 测试**从不运行**），
  并加 `tests/test_frontend_leaf_suite.py` 守 CI 接线本身。
- ✅ **3.3 已修（大部分）** —— `app.js` 里三个够不到的纯逻辑段抽成 leaf
  （`backend_panels.js` / `scan_panel.js` / `chart_frame.js`，+30 条 node 测试）；
  `heatmap.js` 因像素哈希护栏性质不同而推迟。
- ⏭ **下一个：§4.6**（`test_lab_ui.py` 的 24 条源码字符串断言 —— 已定策略：
  保留但标注为「源码形状守卫」，并加 meta-guard 防止新测试静默混入）。

| # | 严重度 | 位置 | 一句话 |
| --- | --- | --- | --- |
| **1.1** | ✅ **已修** | `cvsim/fock/ir.py` | ~~fock `validate_ir` 缺模索引范围 / 负值 / 参数类型校验~~ **已补齐全部 23 项**（实测缺 6 组：模索引 3 / arity 2 / 参数值 11 / `params` 容器与必填 4 / `id` 3 / 扩展字段 4）；新增 `tests/test_ir_parity.py` 守卫；**顺带发现并修了 kraus 实数 dtype 无法 `from_ir` 的真 bug** |
| **4.1** | ✅ **已修** | `tests/test_lab_ui.py:664` | ~~101 字符 > 100 → CI lint 红~~ **本工作区已修复**：tuple 折成两行，`ruff check` → `All checks passed!` |
| **3.1** | ✅ **已修** | `cvsim/lab/static/editor.js` | ~~回落分支读 `s.irToUiOp`，但 `app.js:855` 发布的是 `uiToOp` → op 改名静默失效~~ **实测比原报告更糟：三个键全错**（`irToUiOp`/`v1ToUiParam`/`fockV1ToUiParam` 对 `uiToOp`/`uiToParam`/`fockUiToParam`），op 改名、`theta→phi`、fock `T→eta` 三路全废；中间态**已删**（回归 docstring 声明的两态契约，而非原报告建议的 fail-fast —— 那会red 76 处测试＝改契约）；`schemaTables` 已从 import 移除，新增行为+结构 2 守卫 |
| **3.4** | ✅ **已修** | `cvsim/lab/static/editor.js` × `fock.js` × `initial.js` | ~~`setInitial` 不按 cutoff 夹取，但 `editor.js:781` 明确断言"clampInitial 把 initial 夹到 cutoff-1"；`cutoff=2` + 输入 `9` → `initial=[9]`、标签 `\|9⟩`、`/run` 422~~ **已修**：`clampInitial` 归位 `initial.js`（fock 语义单点），`setInitial` 里调且**限定 fock 分支**（bosonic 源名不能被当数字夹）；新增 Edge 探针 `tests/lab_initial_clamp_probe.mjs` 真实敲 `9` 验证 —— 删 clamp 即复现 `422 initial[0]=9 must be in [0, 2)` + `\|9⟩` |
| **4.2** | ✅ **已修** | `.github/workflows/ci.yml` | ~~CI 六个任务无 node 步骤 → **9 个 `*.test.mjs` 从不运行**~~ **已加第七个任务 `frontend`**（`node --test tests/*.test.mjs`，glob 由 shell 展开 → 新测试自动纳入；pin `node-version: "22"`）；配套 `tests/test_frontend_leaf_suite.py` 守卫 CI 接线本身（6 种腐烂变异全部被抓） |
| **4.6** | ✅ **已修（策略：标注而非删除）** | `tests/test_lab_ui.py` | 31 个测试里 **24 个**含 `read_text()` 抓 JS 源码做字符串断言（+1 个 shell out），仅 **6 个**纯行为测试 —— 改局部变量名就红，行为坏了反而可能绿。**已修**：文件头声明分层（leaf=`*.test.mjs` / 行为=probe / **源码形状=此处**）、`SHAPE_GUARDS` + `BEHAVIOUR_TESTS` 两张登记表（每条附一句"为什么它确实属于形状层"）、`test_shape_guards_are_declared_not_silently_behavioural` meta-guard 保证新测试无法静默混入；`test_scan_dirty_key_*` 与 `test_fock_theme_vars_*` 的行为主体已迁 leaf，原测试退化为**只断言接线边**；离线 URL 守卫改为**按 import 图发现**全部前端文件（新 leaf 自动纳入，已变异验证） |
| **2.3** | ✅ **已修** | `cvsim/lab/ir.py` | ~~`_wigner_mode_guard_fail` 逐字节重复两份 + bosonic 跨包 import；ADR-0010 #5 登记例外、测试开洞放行~~ **已按 ADR 原文归位为 `ir.py:check_wigner_mode`**（模板+比较一起单点，五处调用点各自手写的 `if mode >= nmode` 收编）；两份定义与跨包 import 消失，测试开洞删除并换硬断言；**原报告建议的 `result.py` 是错的**（违反 `result.py` 只 import numpy 的守卫、且成环、且 ADR 自己已否决） |
| **2.1** | ✅ **已修** | `gaussian_backend.py:179,188,191,233` | ~~Lab 穿透 `CompiledCircuit` 私有面（`_init_state` / `_segments` / `_apply_merged` / `_run_op`），按 gaussian 私有实现写死~~ **已修**：范围实测**只有 gaussian 后端**穿透（fock 走 `.run()`、bosonic 走公开 `run_steps()`）；原稿"把 `segments` 升为公开"**被否**——`CONTEXT.md:132` 已冻结"不暴露段布局"；改为基类新增公开 `run_breaks(on_break)` + `run_op()`（回调收 IR 下标，段布局留私有），`run()` 内部复用 `run_breaks`（遍历 2 份→1 份），4 个私有调用点清零，2 条守卫 + 变异验证 |
| **4.3** | 🟠 High | `tests/` | 扁平目录混四类东西：108 pytest + 9 node 单测 + 11 CDP 探针 + 2 个非测试 `_adversarial_*_review.py` |
| **4.4** | 🟠 High | `tests/` 与探针 | 探针硬编码 Windows Edge 路径 + `.venv/Scripts/uvicorn.exe`，无 `process.platform` / 环境变量覆盖 → ubuntu CI 永不可跑；端口手工分且撞车 |
| **1.2** | ✅ **已修** | 三份 `ir.py` | ~~`_is_num`/`_is_leaf_pair`/`_check_value` 逐字节相同~~ **四个值校验 helper 已提进 `cvsim.circuit_common`**（`is_num`/`is_leaf_pair`/`check_matrix`/`check_value`，各包保留私有别名）；`_json_defaults` 也统一走 `circuit_common.json_defaults`，bosonic 不再退化成 `dict(defaults)`。**未修**：`_decode` 各包的表示特有分支（属 §1.3 范畴） |
| **1.3** | 🟡 Medium | `gaussian/compile.py` × `bosonic/compile.py` | `_BREAK_OPS`/`_REMOVE_MODE_OPS`/`_factor`（`:70` × `:69`）/`_instantiate`（`:104` × `:102`）近乎逐字相同，同样无守卫 |
| **2.2** | ✅ **已修** | `cvsim/lab/dispatch.py` | ~~三处 `backend ==` 特判，与 ADR-0010「注册表加一行即接入」相反~~ **已修**：`steps` 两处纯冗余已删（bosonic 自读 `circuit.detail`，ADR-0010 #4 本就落地）；`rng` 差异改为注册表行 `_Runner(callable, wants_rng)`，`run_circuit`/`sample_circuit`/`_invoke` 函数体零 backend 比较；新增 AST 分支守卫 + 第四后端"只加一行"可执行声明 + 3 条 rng 语义行为等价守卫；变异 3 种全部被抓（bosonic 标志翻 False 红 2 条，fock 标志翻 False 只红标志断言 —— 因 fock 内部已兜种子，该负结果写进 docstring） |
| **3.2** | 🟡 Medium | 3 个 store + 3 份改名表 | schema 单点注入实际是**三个并行 store**（`schema_store.js:10-11` / `editor.js:82-83` / `initial.js:15`），同一改名事实正反手写两遍 + 第三份惰性拷贝 |
| **3.3** | 🟡 Medium | `app.js` | 0 export，~330 行逻辑（4 个候选 leaf）`node --test` 够不到；6 个模块级缓存无 `invalidate()` |
| **3.7** | 🟡 Medium | `schema.py:142` | `/schema` 已下发 `extensions.sweepable`，**前端零消费**，反而重推 5 次 `Array.isArray(d.sweep)` |
| **4.7** | 🟡 Medium | `tests/` | **30 处**测试 import cvsim 私有名（**17 个文件**，AST 实测），而 `test_public_api.py:96-119` 的 AST 守卫**只覆盖 1 个文件** |
| **1.4/1.5** | 🟡 Medium | 3 处 | `_MERGEABLE_OPS`（3 处声明 0 读取）、`LAB_RESULT_CORE_KEYS`（0 消费者）—— 死声明 |
| **4.8** | ✅ **已修** | `pyproject.toml` / `conftest.py` | ~~coverage 无 `fail_under`；9 个 `phaseB*` marker 中 `phaseB9`/`phaseB10` 从未使用且 CI 无 `-m phaseB*` 任务；`conftest.py` 大半死代码；mypy `tests.*` override 是死配置~~ **已修**：`fail_under = 90`（实测基线 92%，并已变异验证门会红）；删 12 个死符号（`conftest.py` 169→101 行）；删死 mypy override；`omit` 通配符改逐一列出（原通配把**被测试的** `m4_cross_rep.py` 也盖住了）；修 `b7` 误标 + 补 `b9`/`b10` 漏打的 marker（原报告说"B9/B10 从未使用"其实**说反了**：文件存在、只是没打标记） |
| **4.9** | 🟡 Medium | golden | 逐字节 `assert body == golden`，浮点来自 numpy RNG 流，而 `uv.lock` 的 numpy 按 Python 版本分叉 → 只在捕获版本上可靠 |
| **2.4-2.7** | 🟢 Low | `cvsim/lab/*` | `scan.py` 重复校验块、`schema.py`/`ir.py` 职责劈半、`_load_fock`/`_load_bosonic` 结构镜像、`server.py` 重复 |
| **3.5/3.6/3.8** | 🟢 Low | 前端 | 两个 GET（`app.js:844,867`）绕过 `requestLab`、`app.js:24-63` import 期抓 22 句柄 + `editor.js:384` 全局 keydown、6 类重复构造 + 一批死代码 |
| **4.10-4.11** | 🟢 Low | 杂项 | ~~`.gitignore:59` 匹配不到 `*.log.crash`~~ ✅ **已修**（改 `lab_server*.log*`，`git check-ignore` 已命中，crash + 4 个陈旧 `.log` 已删）；ADR 缺 0013、`.scratch` 引用、`examples/` 绕过公开导入、`test_gkp_tutorial.py` 重写被跟踪 notebook **仍未修** |
| **4.3** | ✅ **已修** | `tests/` | ~~扁平目录混四类东西、无 `tests/README.md`~~ **已修**：`_adversarial_*_review.py` 两个手工脚本收进 `tests/probes/`；补 `tests/README.md`（跑法矩阵 + 三层分工 + 探针环境变量 + 三套 golden 重生成命令 + marker 说明 + 环境警告）。**未做**：`tests/{unit,integration,golden,frontend}/` 全拆分（收益低、churn 高） |
| **4.4** | ✅ **已修** | 12 个探针 | ~~硬编码 Windows Edge 路径 + `.venv/Scripts/uvicorn.exe`，无 platform 分支/环境变量 → ubuntu CI 永不可跑~~ **已修**：新增 `tests/probe_env.mjs`（`EDGE_PATH`/`UVICORN`/`PROBE_PORT`/`PROBE_CDP_PORT`，platform 默认值，profile 写系统临时目录）；12 个探针全部改接；实测跑通真实 CDP 探针 5/5 PASS。**未做**：让探针在 ubuntu CI 上真跑（需装浏览器，另议） |

### 已解决（本审计之前已由工作区改动处理，仅作记录）

| 原发现 | 现状（`1e207cd` 实测） |
| --- | --- |
| 根目录 61+ 个 `.probe-*`（约 3 GB）孤儿缓存 | **已清零**（`Get-ChildItem -Directory -Filter ".probe-*"` → 0）。AGENTS.md 已新增纪律："浏览器探针生成的临时的 .probe* 文件使用完了就要删除" |
| `.scratch/` 12 个文件已删除未提交（411 行），且未被 gitignore | **已恢复**（12 个文件在位，`git status .scratch` 干净）。注意 `.scratch/` 仍**未**被 gitignore（`git check-ignore` exit 1）—— 若刻意入库则无需处理 |
| `lab_server.{err,out}.log.crash` 未跟踪且未忽略 | **已修**（§5 row 11）。`.gitignore:56` 改 `lab_server*.log*` — `git check-ignore -v` 现命中 `lab_server.err.log.crash`；两个 crash 文件连同 4 个陈旧 `lab_server*.log` 已删。**但根因仍在**：这些是运行时产物，正确修法是让 server 写到 `os.tmpdir()`，不是靠 ignore 兜 |

---

## §5 建议实施顺序

前 4 项是"修 bug + 把守卫建起来"，性价比最高；5 起是结构重构，建议独立成票。

| 顺序 | 项 | 理由 |
| --- | --- | --- |
| 1 | ~~修 `tests/test_lab_ui.py:664`（§4.1）~~ ✅ **已完成** | CI lint 已恢复全绿 |
| 2 | ~~补 fock `validate_ir` 校验（§1.1）~~ ✅ **已完成**（实际补了 **23 项**，非初报的 3 项） | 曾是唯一会给出错误物理结果的真 bug（负模静默成功）+ 打穿 422 契约；顺带修掉 `apply_unitary` 的 arity 错标与实数 kraus 无法 `from_ir` |
| 3 | ~~加三表示 IR 校验等价守卫测试（§1.1）~~ ✅ **已完成**（`tests/test_ir_parity.py`，60 用例 + 变异测试验证） | 把"合法的镜像"从"靠人记得对齐"变成"机器盯着" |
| 4 | ~~加 `node --test` CI 任务（§4.2）~~ ✅ **已完成**（glob 而非硬编码列表 + 接线守卫测试） | 整个前端 leaf 契约层此前不在 CI 里 —— 已补上 |
| 5 | ~~`_wigner_mode_guard_fail` 收进 `lab/ir.py`（§2.3）~~ ✅ **已完成**（按 ADR-0010 #5 原文命名 `check_wigner_mode`，连带收编五处手写比较） | 消掉 ADR-0010 #5 的注册例外 + 测试开洞 |
| 6 | ~~修 `editor.js:150` 的 `s.irToUiOp`（§3.1）~~ ✅ **已完成**（三个键全错，删中间态回归两态契约；未采纳原报告的 fail-fast） | 潜伏缺陷 |
| 7 | ~~`setInitial` 接 `clampInitial`（§3.4）~~ ✅ **已完成**（`clampInitial` 归位 `initial.js` + 限定 fock 分支；Edge 探针行为验证） | 与自身注释矛盾、可复现 422 |
| 8 | ~~`CompiledCircuit` 私有钩子升为公开协议（§2.1）~~ ✅ **已完成**（未升 `segments`，改公开 `run_breaks`/`run_op`——`CONTEXT.md:132` 冻结"不暴露段布局"） | 表示可移植性的前提 |
| 9 | ~~拆 `app.js` 的 leaf（§3.3）+ `test_lab_ui.py` 源码断言改造（§4.6）~~ ✅ **已完成**（三个零 DOM leaf +30 条 node 测试；`heatmap.js` 因像素哈希护栏性质不同推迟；§4.6 定案为"分层标注 + 退化为接线断言"而非删除） | 互为依据：先有 leaf 才有的可测 |
| 10 | ~~`dispatch.py` 三处特判收进注册表（§2.2）~~ ✅ **已完成**（`steps` 两处纯冗余已删；`rng` 改为注册表行 `wants_rng` 标志；AST 分支守卫 + 第四后端"只加一行"可执行声明） | 恢复 ADR-0010「一行一后端」 |
| 11 | ~~清理批次：`.gitignore` 改 `lab_server*.log*`、`_adversarial_*_review.py` 挪进 `tests/probes/`、探针平台路径改环境变量、补 `tests/README.md`、`conftest.py` 删死符号、coverage `fail_under`（§4.3/4.4/4.8/4.10）~~ ✅ **已完成**（六项全做；`fail_under=90` 实测基线 92% 且变异验证会红；12 个探针改 `probe_env.mjs` 并**实测跑通真探针 5/5**；`conftest.py` 169→101 行；另发现并修了原报告说反的 marker 问题） | 各自独立、低风险 |
| 12 | **结构性**：`compile.py` 算法镜像（§1.3）、死声明清理（§1.4/1.5）、`scan.py`/`schema.py`/`ir.py` 收敛（§2.4-2.6）、前端 schema 单点（§3.2/3.7）、§4.7 私有名测试 import、§4.9 golden 脆弱性。**注**：§1.2 的 `circuit_common` 值校验部分**已完成**，此处只剩算法镜像 | 需要 ADR 背书（可能 amend ADR-0001/0004/0010）—— **下一个该做的** |

---

## §6 基线复现（`1e207cd`）与当前状态

```bash
# Python —— 审计基线（仅 §4.1 ruff 修复）：1508 passed, 12 skipped
# Python —— 修完 §1.1 + §1.2 值校验后：1575 passed, 12 skipped
# Python —— 再加 §4.2 接线守卫（+5）：1580 passed, 12 skipped
# Python —— 再加 §2.3 守卫（+2）：1582 passed, 12 skipped
# Python —— 再加 §2.1 守卫（+2）：1584 passed, 12 skipped
# Python —— 再加 §3.3/§4.6 守卫（+1 meta-guard）：1585 passed, 12 skipped
# Python —— 再加 §2.2 守卫（+7）：1592 passed, 12 skipped
# Python —— §5 row 11 清理批次后**仍为 1592 passed**（无新增测试；
#          但 b7 marker 误标→正、b9/b10 补 marker 后 -m 选择器才生效）
.venv/Scripts/python.exe -m pytest -q

# 覆盖率门（§4.8 新增，实测基线 91.69%，门设 90%）
.venv/Scripts/python.exe -m pytest --cov=cvsim --cov-report=term
# 变异验证：只跑单个测试文件 → 34.29% → FAIL Required test coverage of 90.0% not reached（exit 1）

# Node —— 前端叶子测试（§3.1 后：editor 65 → 66；§3.4 再 +3 → 159 总；
#          §3.3 新增三个 leaf 测试文件 +30 → 189 总，12 个文件）
node --test tests/*.test.mjs

# 浏览器行为探针（本地，需 Edge + 真实 uvicorn；§3.4 新增）
node tests/lab_initial_clamp_probe.mjs

# node leaf 契约层（189 pass, 0 fail）—— §4.2 已把它接进 CI（frontend 任务）
node --test tests/*.test.mjs
# 等价于显式列 12 个文件（shell 展开后 node 收到的是文件列表）：
node --test tests/backend_panels.test.mjs tests/chart_frame.test.mjs \
  tests/colormap.test.mjs tests/curve.test.mjs tests/editor.test.mjs \
  tests/fock.test.mjs tests/request.test.mjs tests/scan_form.test.mjs \
  tests/scan_panel.test.mjs tests/schema_merge.test.mjs \
  tests/steps_slider.test.mjs tests/svg_kit.test.mjs

# ⚠ 目录模式不可用（实测 node v24.11.0）：
#   node --test tests/  →  Error: Cannot find module '...\tests'（1 test, 1 fail）

# lint（修复 §4.1 + §1.1 后：All checks passed!）
.venv/Scripts/python.exe -m ruff check --output-format=concise

# type check（Success: no issues found in 62 source files）
.venv/Scripts/python.exe -m mypy cvsim/
```

环境：**Python 3.13.5 + numpy 2.5.1 + scipy 1.18.0 + jax 0.11.0**。

> ⚠ **pytest 数字取决于 venv 里有没有 jax**：
> 主 `.venv` 装了 jax，所以 **1508 passed / 12 skipped**；
> 而用 `uv sync --frozen` 新建的裸 venv（lock 里无 jax）则是 **1435 passed / 85 skipped** ——
> 差额 **73 = 新增 pass = 减少的 skip**（那 73 个是 jax 测试）。本文档早期草稿引用的 1435/85 即后者。
> 比对基线数字前先确认 jax 是否在环境里。
>
> `thewalrus` 的 12 个 skip 是因为 **numba 要求 numpy ≤ 2.4，而本项目锁 2.5.1** ——
> 属于依赖冲突，非本审计范围。

注意：`uv` 的默认解释器选择是 3.10（→ numpy 2.2.6），与本基线不同；
**逐字节 golden 测试对 numpy 版本敏感**，换版本前先确认。

### §5 row 11 清理批次的实测数字

| 项 | 前 | 后 |
| --- | --- | --- |
| `tests/conftest.py` 行数 | 169 | **101** |
| `tests/conftest.py` 零引用符号 | 12 | **0** |
| coverage 门 | 无（`fail_under` 缺省 0） | **90**（实测基线 **91.69%**：6095 stmts / 381 missed / 2258 branch / 283 partial） |
| coverage `omit` | `cvsim/demos/*`（误盖被测的 `m4_cross_rep.py`） | 4 个**真的**无人执行的 demo 脚本（`m4_cross_rep.py` 回统计） |
| mypy `tests.*` override | 1 条死配置 | **0** |
| 探针硬编码 Edge/uvicorn 路径 | 12 个文件 | **0**（全走 `tests/probe_env.mjs`） |
| 探针撞车端口对 | 2 对（8860+9224、8771+9229） | **0**（`PROBE_PORT`/`PROBE_CDP_PORT` 可覆盖） |
| 探针往仓库根写 profile | 12 处 | **0**（走系统临时目录） |
| `tests/` 根的非测试 `.py` | 2 | **0**（入 `tests/probes/`） |
| pytest / node 计数 | 1592 / 189 | **1592 / 189**（无变化 —— 本次是清理与守卫配置，不新增测试） |

新增文件：`tests/probe_env.mjs`、`tests/README.md`；新目录 `tests/probes/`。

**变异验证**：`fail_under` 真的会红（单文件跑 → 34.29% → exit 1）；
marker 修复真的生效（`-m phaseB9` 由 0 选中 → **6 passed, 11 deselected**）；
探针改造真的跑得通（`node tests/lab_initial_clamp_probe.mjs` → 真实 uvicorn +
headless Edge + CDP，**5/5 PASS**，exit 0）。

### 复测截断窗口

往本文加内容后，用这段重新测"哪些标题还在 32768 字节窗口内"：

```python
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows 控制台默认 GBK，会炸
p = "docs/review-09-18-module-boundaries.md"
txt = open(p, "rb").read().decode("utf-8")
print(f"bytes: {len(txt.encode('utf-8'))}")
for ln in txt[:32768].splitlines():
    if ln.startswith("#"):
        print("  IN  " + ln[:72])
off = 32768
for ln in txt[32768:].splitlines(keepends=True):
    if ln.startswith("#"):
        print(f"  OUT @{off} {ln.strip()[:72]}")
    off += len(ln.encode("utf-8"))
```

> ⚠ 用 PowerShell 的 `Get-Content` / `Select-String` 量中文文档会按 GBK 误解码，
> 行长度与字节数都会算错 —— 必须用 Python 按 UTF-8 读。

---

## §1 表示包镜像无漂移守卫

ADR-0001 禁止三个表示包互相 import，因此三份 `ir.py` / `compile.py` 的镜像**是契约要求的，不是坏味道**。
问题在于：镜像合法，但**只守了 arity，没守行为**，于是已经漂了 ——
§1.1 就是漂移的实测证据。✅ **§1.1 已修，并补上 `tests/test_ir_parity.py` 作为漂移守卫**；
§1.3（`compile.py` 算法镜像）**仍无守卫**，是同类问题里剩下的那一半。

### 1.1 ✅ 三份 `validate_ir` 行为不一致（**已修**；原判"缺 3 项"实为 **23 项**）

位置：`cvsim/gaussian/ir.py`、`cvsim/fock/ir.py`、`cvsim/bosonic/ir.py`

> **原报告低估了范围。** 初版只列了 3 项（模索引范围 / 负值 / `_check_value`）。
> 实施修复时逐条比对三份实现，**实测缺口是 6 组共 23 项**。下面是从"三表示行为一致"出发逐条探针的结果。

fock 的 ops 循环原本**只**检查 arity 与"参数名是否在 `meta.value_kind` 里"，其余全放行。
补全过程中发现 fock 是照着 gaussian 的一个**早期快照**抄的，后来 gaussian/bosonic
加了校验而 fock 没跟 —— 这正是"镜像无守卫"的必然结果。

实测缺口（修复前，gaussian 与 bosonic 在所有用例上一致，只有 fock 偏离）：

| 组 | 缺的检查 | 用例数 |
| --- | --- | --- |
| A 模索引 | 负值、`bool`、`>= nmode` | 3 |
| B arity | `all`（须等于 `range(nmode)`）、`any`（≤1） | 2 |
| C 参数值 | `num` 收到 str/list/bool、非法 dict 形式、`$param` 非串/多余键、`$ref` gain 非数/多余键、矩阵不齐、空串 | 11 |
| D `params` 容器 | 非 dict、缺 `params` 键、必填参数缺失 | 4 |
| E `id` | 空串、非串、重复 | 3 |
| F 扩展字段 | `view`/`ui` 非 dict、`seed` 负数/`bool` | 4 |

修复前的后果（实测 `FockCircuit.from_ir(...)` → `.run()`）：

| 输入（`nmode=1`） | gaussian / bosonic | fock（修复前） |
| --- | --- | --- |
| `modes: [5]` | REJECT | `from_ir` **放行** → `run()` 抛裸 `IndexError: list index out of range` |
| `modes: [-1]` | REJECT | `from_ir` **放行** → `run()` **静默成功**（负索引回绕，算出错误物理） |
| `params: {"r": "oops"}` | REJECT | `from_ir` **放行**，当成符号参数 `frozenset({'oops'})` → `run()` 抛 `ValueError: Missing parameter 'oops'` |

**为什么曾是 Critical**：前两条不是"错误消息不好看"，是**同一 payload 三后端语义不一致**，
且其中一条（负模）会静默返回**错误的物理结果**。第三条打穿了 Lab 的 422 契约 ——
server 的 `DOMAIN_ERRORS` 只收 `CircuitV0Error` / `ValueError` 系，裸 `IndexError` 会变成 500。

`tests/test_architecture.py` 抓不到：它只查 arity 结构，不查值域行为。

#### 已实施的修复

1. **四个值校验 helper 提进 `cvsim/circuit_common.py`**（ADR-0004 已开这个位，且在
   `test_architecture.py:20` 的 root allowlist 内）：`is_num` / `is_leaf_pair` /
   `check_matrix` / `check_value`（外加 `check_kraus`）。gaussian/bosonic/fock 三边
   都 import 它，各自保留 `_is_num = is_num` 这类私有别名，**调用点与历史名不动**。
2. **fock `validate_ir` 按 gaussian 逐项对齐**：模索引三段检查、arity 五分支、
   `id` 三段、`params` 容器与必填、扩展字段浅类型检查全部补齐。
3. **`_ARITY_MAX` 删除**（补齐后不再有调用点）。
4. **顺带修掉 §1.2 的 `_json_defaults` 漂移**：三边统一走 `circuit_common.json_defaults`，
   bosonic 不再退化成 `dict(defaults)`（原会往"JSON-native"载荷里漏 np 对象）。
5. **新增守卫 `tests/test_ir_parity.py`**：60 个用例，同一 payload 喂三个 `validate_ir`，
   断言 accept/reject 一致；并断言**任何异常都必须是 `ValueError`**（`TypeError`/`IndexError`
   会打穿 Lab 的 422 契约，这正是原 bug 的形态）。

#### 修复中额外发现的两个真 bug（均已修）

**(a) fock `apply_unitary` 的 arity 标签一直是错的 —— 而且因此从未被校验。**
fock 给 `apply_unitary` 标的是 `arity="any"`，但 `"any"` 在 gaussian/bosonic 里意味着
**至多 1 个模**（它们的 `amplifier`/`phase_noise` 签名是 `mode: int | None`）。
fock 的 `apply_unitary` 实际是 **k-local**（任意个不重复的模，`[]` = 全空间），
`tests/test_fock_ir_f3.py:78` 就合法地用了 `modes=[1,2]`（3 模电路）。
照抄 gaussian 的 `"any"` 规则会**误拒**合法 payload（我在实现中真的踩到了，被该测试抓到）。
→ 新增 arity 值 **`"subset"`**（fock 专用，语义：任意个**互不重复**的模，`[]` = 全空间），
并加守卫 `test_fock_only_arity_is_not_gaussian_any` 锁住这个区分。
同时补上**重复模检查**（`[0,0]` 能建好、跑到 `run()` 才炸 `ValueError: repeated axis`）。

**(b) 实数 dtype 的 `kraus_ops` 无法 `to_ir` → `from_ir`。**
`to_ir` 按算子实际 dtype 输出（全实数矩阵编成嵌套实数），但 `_decode` 的 kraus 分支
**写死了 `[re, im]` 对**，于是读自己吐出来的文档直接 `TypeError: 'float' object is not subscriptable`。
损失算子的 `sqrt(T)` 分解全是实数，这条路径并不冷门。
→ `_decode` 抽出 `_decode_matrix`（实数/复数自适应），`check_kraus` 复用 `check_matrix`
（同样两形态都收），并加回归测试 `test_roundtrip_kraus_ops_real_dtype` 与
6 个畸形 kraus 用例 `test_validate_rejects_malformed_kraus`。

#### 验证

```
ruff check                          →  All checks passed!
mypy cvsim/                         →  Success: no issues found in 62 source files
pytest tests/test_ir_parity.py      →  60 passed
pytest（全量）                      →  1575 passed, 12 skipped
```

（基线 1508 + 新增 60 等价守卫 + 7 个 kraus 回归 = 1575，数目吻合。）

**变异测试**（确认守卫真能抓回归，不是摆设）：逐条把补上的检查重新"打瞎"，
`test_ir_parity.py` 分别红 4 / 11 / 2 个用例 —— 三组检查都被独立抓到。

### 1.2 ✅ 编解码镜像逐个比对结果（**值校验部分已修**）

脚本逐字比对函数体（去 docstring / 注释 / 空行）后：

| 函数 | 结论 |
| --- | --- |
| `_is_num` / `_is_leaf_pair` / `_check_value` | gaussian ≡ bosonic **逐字节相同** |
| `_check_matrix` | 仅差一处行内注释（`style` 参数注释） |
| `_json_defaults` | gaussian ≡ fock；**bosonic 退化成 `return dict(defaults)`**，不做 np 标量/数组归一化 |
| `_encode` | 三份各异（fock 多 kraus / `np.generic` 分支，bosonic 无 `$ref` 分支） |
| `_decode` | fock 多 `kind == "kraus"` 分支；**bosonic 缺 `"$ref" in v` 分支** |
| `kraus` 值形态校验 | **原本只有 fock 有**（`kraus` 是 fock-only 的 `value_kind`），且写死 `[re, im]` 对 —— 与自家 `to_ir` 的实数输出不兼容（见 §1.1 (b)） |

`bosonic._json_defaults` 不归一化是个**潜伏错误**：核心 `ir_schema()` 的 defaults 一旦引入
numpy 标量/数组，bosonic 会把 np 对象原样塞进"JSON-native"的 schema 载荷
（`cvsim/lab/schema.py:148-155` 的 docstring 明确声称"JSON-native end to end"）。

**已修（随 §1.1 一起做）**：四个值校验 helper（`is_num` / `is_leaf_pair` /
`check_matrix` / `check_value`）提进 `cvsim/circuit_common.py`，三个表示包 import 共享版，
各自保留私有别名。`_json_defaults` 也一并统一到 `circuit_common.json_defaults`
（numpy 归一化），bosonic 的退化实现删除 —— 上面的潜伏错误因此在结构上不可能再出现。
`check_kraus` 是**新抽出来的**（原本没有独立函数），并改为复用 `check_matrix`，
实数/复数两形态都收。

**未修（有意留下）**：`_encode` / `_decode` 的表示特有分支。
它们**本来就是各包不同的**（fock 的 kraus、bosonic 缺 `$ref`），
硬合会造出一个"按 kind 分派到各表示"的伪共享函数，比现在更难懂。
这部分归 §1.3（算法镜像）时一并处理。

### 1.3 🟡 `gaussian/compile.py` ⟷ `bosonic/compile.py` 算法镜像

| 符号 | gaussian | bosonic |
| --- | --- | --- |
| `_BREAK_OPS` | `compile.py:40` | `compile.py:39` |
| `_REMOVE_MODE_OPS` | `compile.py:52` | `compile.py:51` |
| `_MERGEABLE_OPS` | `compile.py:54` | `compile.py:53` |
| `_factor` | `compile.py:70` | `compile.py:69` |
| `_instantiate` | `compile.py:104` | `compile.py:102` |

`_factor` / `_instantiate` 是**真算法**（把 op 元组分解成 symplectic 因子 / 实例化成矩阵），
diff 出来只有一行注释的差别。一处修 bug 另一处不修 = 静默发散。

**修法**：与 §1.1 合并 —— 算法能共享的提到 `cvsim.circuit_common`，
表示特有的（哪些 op 可合并）留在各包并**加等价守卫**。

### 1.4 🟡 `_MERGEABLE_OPS` 是死常量（已核实 0 读取）

声明 3 处、**读取 0 处**、测试 0 引用：

- `cvsim/gaussian/compile.py:54`
- `cvsim/bosonic/compile.py:53`
- `cvsim/fock/circuit.py:65`

核实方式：全 `cvsim/` + `tests/` 搜 `_MERGEABLE_OPS`，排除 `^\s*_MERGEABLE_OPS\s*[:=]` 的赋值行 → 0 命中。
`compile_segments` 实际只收 `break_ops` / `remove_mode_ops`（见 `gaussian/compile.py:138-139`）。

**修法**：删；或让它真的参与合并判定（若合并判定确实需要它）。

### 1.5 🟡 `LAB_RESULT_CORE_KEYS` 死声明

`cvsim/lab/result.py:66-68` 声明了核心响应键集（`schema`/`backend`/`nmode`/`wigner`/`meters`/`measured`/`seed`/`sampled`），
**全库零消费者**。`check_meters()` 只守 meter 键，不守这个。

**修法**：让 `tests/test_lab_golden.py` 拿它断言每个 golden 响应都含这套核心键
（这正是 ADR-0008 决策 4 想要的"公共核心必填"守卫），或直接删。

---

## §2 `cvsim/lab/` 内部边界

### 2.1 ✅ Lab 穿透 `CompiledCircuit` 私有面（**已修**）

修复前 `cvsim/lab/gaussian_backend.py::_execute` 直接调：

| 私有面（修复前） | 行 |
| --- | --- |
| `compiled._init_state()` | `:179` |
| `compiled._segments` | `:188` |
| `compiled._apply_merged(ops, nmode, {}, state)` | `:191` |
| `compiled._run_op(seg[1], state, ...)` | `:233` |

`CompiledCircuit` 是 ADR-0004 定义的**三表示共用基类**，Lab 却按 gaussian 的私有实现把调用面写死了。
换个表示的编译产物，Lab 这块直接废。

**范围校正**：只有 `gaussian_backend.py` 穿透。`fock_backend.py` 走 `fc.run(...)`
（`:152`）、`bosonic_backend.py` 走 `bc.compile().run_steps(...)`（`:116`）——两者都在公开面上。
所以这不是"三后端都坏"，而是**一个后端坏 + 另外两个各自造了公开出口**。

**修法（与原设想不同）**：原稿写的是"把三个钩子升为公开协议（`init_state()` /
`segments` / `apply_merged()`）"，但 `CONTEXT.md:132` 明确冻结了 `CompiledGaussian`
的公开面：

> 公开面仅 {nmode, params, run}；多次 run 独立随机，**不暴露段布局**。

`segments` 一旦公开，就是直接违反这条已冻结契约——那不是修 bug，是改契约。
`CompiledBosonic.run_steps()`（`bosonic/compile.py:266`）给出了正确形状的先例：
**公开一个"带检视点的执行方法"，而段布局留在私有面**。

落地：

- `cvsim/circuit_common.py::CompiledCircuit` 新增公开 `run_breaks(on_break, **values)`
  ——遍历仍在基类里，merged 段自己消化，**每个断点把 `(op, state, results, ir_idx)` 交给回调**。
  Lab 拿到的是 IR 节点下标，不是段布局，于是它再也不需要读 `_segments`。
- 新增公开 `run_op(op, st, results, *, rng=None, **values)` ——`_run_op` 的公开包装，
  给"自己驱动遍历"的调用方用。
- `run()` 改为内部走 `run_breaks`（**遍历逻辑从 2 份变 1 份**）。
- `gaussian_backend.py::_execute` 的段循环整体收进本地 `on_break` 回调，
  `_init_state` / `_segments` / `_apply_merged` / `_run_op` 四个私有调用点全部消失。

守卫：`tests/test_lab_backend_symmetry.py:test_lab_does_not_touch_compiled_private_surface`
（三个后端源码里禁止出现 `._init_state` / `._segments` / `._apply_merged` / `._run_op`）
+ `test_compiled_circuit_public_protocol`（协议本身存在、有 docstring、
**且不得出现 `segments` / `init_state` / `apply_merged` 三个公开别名**——
把"不暴露段布局"钉住；行为上断言 `run_breaks` 与 `run()` 结果一致、
断点 IR 下标正确）。

反向验证：把 `_ = compiled._segments` 重新塞回 `_execute` → 守卫红
（`1 failed, 17 passed`），撤掉即绿。

### 2.2 ✅ `dispatch.py` 三处 backend 特判（**已修**）

`cvsim/lab/dispatch.py` 修复前：

| 行 | 特判 |
| --- | --- |
| `:46` | `rng = ... if circuit.backend != "gaussian" else None` |
| `:48` | `if circuit.backend == "bosonic": return runner(..., steps=...)` |
| `:64` | `if circuit.backend == "bosonic": return runner(..., sampled=True, steps=...)` |

理由都是**真事实**（rng 对 gaussian 无意义、`steps` 只 bosonic 认），但表达方式让
ADR-0010 #1 的"runner 注册表，一行一后端"失效：接入第四个后端时要么被分支漏掉
（rng 不派生 / steps 不传），要么得回来改 `dispatch.py`。

#### 已实施的修复

原报告给了两个选项，实际落地时**逐条核了代码，结论比原报告更细**：

1. **`steps` 分支是纯冗余，直接删。** 三个 runner 的签名**本来就已统一**为
   `(circuit, rng, *, sampled, steps)`（`gaussian_backend.py:239`、
   `fock_backend.py:134`、`bosonic_backend.py:97`），且 `steps` 在非 bosonic
   处声明"接受并忽略"。更关键的是：**bosonic 自己读 `circuit.detail`**
   （`bosonic_backend.py:114` 的 `want_steps = steps or circuit.detail == "steps"`）
   —— ADR-0010 #4 其实**已经落地了**，dispatch 再转发 `steps=` 纯属重复。
   故 `steps` 不需要注册表标志，一律传即可。
2. **rng 分支不能删，但可以变成数据。** 三个后端对 `rng=None` 的**语义不同**，
   这是物理事实而非历史包袱：
   - gaussian：`None` = "走均值路径"（`_apply_measure` 的 `rng is None` →
     `homodyne_mean`），给了 rng 才是真采样。故 `/run` 下**必须**传 `None`。
   - bosonic：`None` = "没给生成器"，测量层自造**未播种** `default_rng()`
     → 同 seed 不可复现。故 `/run` 下**必须**派生。
   - fock：同样会让测量层自造未播种生成器，但 `run_fock_circuit:152`
     **自己兜了** `default_rng(circuit.seed)` → dispatch 派生与否对它**行为冗余**。

   注意 rng 该不该派生**同时取决于后端和动词**：`/sample` 下三者都要派生。
   故注册表行改成 `_Runner(callable, wants_rng)` 的 NamedTuple，
   **`wants_rng` 只描述"非采样路径下要不要派生"**，路由体只剩
   `_invoke()` 一处查表 + 一处调用。

`_RUNNERS` 现在是 `{"gaussian": _Runner(..., wants_rng=False), "fock": ..., "bosonic": _Runner(..., wants_rng=True)}`，
`run_circuit` / `sample_circuit` / `_invoke` 三个函数体内**零 `backend` 比较**。

#### 新增守卫（4 条）与变异测试

| 守卫 | 钉的性质 |
| --- | --- |
| `test_dispatch_routing_has_no_backend_branch` | AST：路由三函数体内不得同时出现 `.backend` 与后端名字面量 |
| `test_runner_registry_rows_declare_rng_need` | 注册表每行都带 `wants_rng`，且值不说谎 |
| `test_new_backend_row_needs_no_routing_change` | "一行一后端"可执行：伪造第四后端只加一行即两动词都跑通 |
| `test_bosonic_run_is_reproducible_per_seed` / `test_gaussian_run_is_mean_path_but_sample_is_true_sampling` / `test_explicit_rng_reaches_gaussian_sampling_path` | rng 语义逐后端行为等价（重构未改物理） |

变异实测（3 种）：
- 把 `row.wants_rng` 换回 `circuit.backend != "gaussian"` → **红 1 条**（AST 守卫）。
- bosonic 的 `wants_rng` 翻 `False` → **红 2 条**（标志断言 + 可复现性）—— 这条是
  真正承载行为的标志。
- fock 的 `wants_rng` 翻 `False` → **只红 1 条**（标志断言），可复现性仍绿 ——
  证实了 fock 的内部兜底确实在起作用，标志对它属**防御性声明**。
  这条负结果**已写进 dispatch docstring 与测试 docstring**，避免后人误以为
  该标志对 fock 是承重的。

### 2.3 ✅ `_wigner_mode_guard_fail` 定义 2 份 + 跨包 import 例外（**已修**）

| 位置（修复前） | 内容 |
| --- | --- |
| `cvsim/lab/fock_backend.py:32-37` | 定义（docstring 自称"Single-point message template"） |
| `cvsim/lab/gaussian_backend.py:110` | **逐字节相同的第二份定义** |
| `cvsim/lab/bosonic_backend.py:27` | 跨包 `from cvsim.lab.fock_backend import _wigner_mode_guard_fail` |

`fock_backend.py:33-36` 的 docstring 自称"Single-point message template (ADR-0010 #5)"，
但它自己就是两份之一。ADR-0010 #5 把这个跨包 import 作为**已注册例外**，
`tests/test_lab_backend_symmetry.py:299-311` 专门开洞放行。

调用点：`fock_backend.py:110,170,255`、`gaussian_backend.py:91`、`bosonic_backend.py:127`。

#### 修复前的实测细节（比原报告更糟）

原报告只说了"两份定义 + 跨包 import"。实际读代码还有两个问题：

1. **函数名与函数体不符** —— 名为 `_wigner_mode_guard_fail`，但它**不做任何判断**，
   只是构造异常。真正的比较 `if mode >= nmode` 由**五个调用点各自手写**。
   所以"模板单点"这句话是**假的**：模板确实是一份文本，但**判断逻辑复制了五遍**。
2. **ADR-0010 #5 的决策文本写的是 `check_wigner_mode(wmode, nmode)`** ——
   代码里根本没有这个名字。也就是说这条 ADR 决策**从未按文本落地**，
   而是以"fock 定义 + gaussian 抄一份 + bosonic 跨包 import"的形式被登记成了例外。

#### 已实施的修复

把**模板与比较一起**搬进 `cvsim/lab/ir.py` 的 **`check_wigner_mode(mode, nmode)`**
（ADR-0010 #5 原文用的就是这个名字，现在名副其实）：

```python
def check_wigner_mode(mode: int, nmode: int) -> None:
    if mode >= nmode:
        raise CircuitV0Error(f"view.wigner_mode {mode} out of range (nmode={nmode})")
```

- fock / gaussian 的**两份定义删除**，bosonic 的**跨包 import 删除**；
  五个调用点变成 `check_wigner_mode(...)` 一行。
- `tests/test_lab_backend_symmetry.py` 的**例外开洞删除**，换成硬断言
  "bosonic 不得 import fock_backend"（连注释豁免都不再需要）。
- 新增 `test_wigner_guard_is_single_point`：断言 422 模板**只**出现在 `ir.py`，
  且三个 backend 里不得再长出同名局部守卫 —— 这正是本次要防的复发。
- 新增 `test_check_wigner_mode_raises_circuitv0error`：行为断言（越界抛
  `CircuitV0Error`，界内 no-op）。

#### 为什么家是 `ir.py` 而**不是**原报告建议的 `result.py`

原报告写"模板搬到 `cvsim/lab/result.py`（三个 backend 都已经 import 它，无新依赖）"。
**这条建议是错的**，三个独立理由：

1. `tests/test_lab_backend_symmetry.py:279` 的 `test_result_py_dependency_bottom`
   **锁死 `result.py` 只能 import numpy/stdlib**（它是依赖图最底层）。
   而模板必须抛 `CircuitV0Error`，那个类定义在 `ir.py`。
2. 现有依赖边 `ir.py:30 → schema.py:30 → result.py` 已经存在，
   再让 `result.py` 依赖 `ir.py` 就成环。
3. **ADR-0010 自己的「权衡」段落已经否决过这个方案**：
   "result.py 章程是「只管响应侧」（模块 docstring 明言），塞执行破坏它"。

`ir.py` 才是正解：它定义 `CircuitV0Error` 与 `View.wigner_mode`，
三个 backend 本来就 import 它，零新依赖、零环。

#### 有意留在各 backend 的东西（不是遗漏）

- **兜底语义**：gaussian → `singular=True`、fock/bosonic → 诚实 null、
  fock batch → raise。ADR-0010 #5 后半段已声明这是**物理事实**。
- **bosonic 的 `state.nmode > 0` 前置条件**：`mode >= 0` 对任何非负模都成立，
  折进共享函数会改变语义（实测 `nmode=0` 在 load 阶段就被拒，
  所以这个分支只在"测量删光了所有模"时到达，确实是 post-run 事实）。

#### 验证

```
ruff check                     →  All checks passed!
mypy cvsim/                    →  Success: no issues found in 62 source files
pytest（全量）                  →  1582 passed, 12 skipped
```

- **422 文本逐字节未变**：三个 runner 实测都返回
  `view.wigner_mode 3 out of range (nmode=2)`，与 golden 一致（是搬移不是改写）。
- **变异测试**：往 `bosonic_backend.py` 里重新塞一个局部守卫 →
  `test_wigner_guard_is_single_point` 立刻红（1 failed）。

### 2.4 🟡 `scan.py` 重复校验块

`scan_circuit`（`cvsim/lab/scan.py:70-71` + `:89-91` + `:92-96`）与
`fidelity_sweep`（`:168-169` + `:196` 起）各有一份**逐字节相同**的
node_id / param / min / max / n 校验。

**修法**：提 `_parse_sweep(sweep, circuit) -> (node_id, param, pmin, pmax, n)`。

### 2.5 🟡 `schema.py` ⟷ `ir.py` 职责被劈两半

`schema.py` 从核心 `ir_schema()` 派生白名单（`cvsim/lab/schema.py:95-119`），
`ir.py` 反向 import 它的 `WHITELIST` / `_EXTENSIONS` / `BOSONIC_SOURCES`。无 import 环，
但"Lab 校验规则"散在两处：

- 边界值的**声明**在 `cvsim/lab/schema.py:138-145`（`_EXTENSIONS`：cutoff max=30、view.n、shots 等）
- 边界值的**消费**却在 `cvsim/lab/ir.py:149-175`（`_parse_view` 里硬编码读 `_EXTENSIONS[...]`）

改一个边界要同时开两个文件，且声明与消费的对应关系不直观。

**修法**：把扩展字段的**校验**也收进 `schema.py`（导出 `validate_view(raw)` 之类），`ir.py` 只做 load 编排。

### 2.6 🟡 `_load_fock` 与 `_load_bosonic` 结构镜像

`cvsim/lab/ir.py:225-265`（`_load_fock`）与 `:268-330`（`_load_bosonic`）是同构的
"白名单前置 → 核心校验 → initial 校验"，只有错误消息与 initial 语义不同。

**修法**：提 `_load_raw(backend, whitelist, validate_fn, initial_check)`。收益中等
（两者只有 ~40 行），但消除了"白名单前置"顺序纪律的重复表达。

### 2.7 🟢 `server.py` 重复

- 本地 `_BATCHABLE = frozenset({"fock"})` 与 `dispatch._BATCHERS` 的键集重复（同一声明两处）
- `except DOMAIN_ERRORS as e: raise _422(e) from e` 重复 ×5

ADR-0010 #6 明确"每路由 except 照旧两行"是**有意的**权衡（route-wrapper 装饰器被否），
所以第二项**不是缺陷**，记录但不建议改。第一项建议改为从 `dispatch._BATCHERS` 派生。

---

## §3 前端 `cvsim/lab/static/`

实测行数（比历史文档的旧数大）：

| 文件 | 行数 | | 文件 | 行数 |
| --- | --- | --- | --- | --- |
| `app.js` | 889 | | `request.js` | 118 |
| `editor.js` | 808 | | `ops_schema.js` | 96 |
| `staff.js` | 478 | | `colormap.js` | 77 |
| `ops.js` | 446 | | `curve.js` | 74 |
| `fock.js` | 429 | | `schema_store.js` | 66 |
| `style.css` | 1392 | | `svg_kit.js` | 41 |
| `index.html` | 233 | | `steps_slider.js` | 41 |
| `initial.js` | 141 | | `scan_form.js` / `default_scene.js` | 20 / 17 |

### 3.1 ✅ `editor.js` 回落分支读不存在的键 → 改名静默失效（**已修**）

`editor.js:140-165` 的 `tables()` 曾有三态：`EDITOR_DERIVED` → `schemaTables()` 中间态 → 本地常量。

#### 修复前的实测：比原报告更糟（三个键全错，不是两个）

原报告说只有 `:150` 的 `irToUiOp` 坏了，而 `:151-152` 的 `v1ToUiParam`/`fockV1ToUiParam`
"恰好对得上发布的键名"。**实测三个键全部对不上**：

| `editor.js` 读 | `app.js:855-857` 发布 | 结果 |
| --- | --- | --- |
| `s.irToUiOp` | `uiToOp` | `{...undefined}` = `{}` |
| `s.v1ToUiParam` | `uiToParam` | `{...undefined}` = `{}` |
| `s.fockV1ToUiParam` | `fockUiToParam` | `{...undefined}` = `{}` |

`{...undefined}` 不报错，静默变空对象 —— 所以整条中间态**三路全废**，不是"部分静默失败"。
三条行为实测（混合态：`publishSchema` 过、`setEditorSchema` 没过）：

```
op 改名      measure_homodyne  →  "ops[0]: op measure_homodyne 不在 Lab 白名单"
参数改名     phase theta=0.9   →  "ops[0].params.phi 必须是有限数值"
fock drop    loss eta=0.5      →  "ops[0].params.T 必须是有限数值"
```

补充发现（原报告未提）：

- **`ops.js:374-378` 读的是对的键**（`s.uiToOp`/`s.uiToParam`/`s.fockUiToParam`）——
  同一个 store，editor 的中间态是**唯一**读错键的消费方。可见键名契约是有的，
  只是这个分支没照抄。
- 该分支还**整体硬编码 extensions**（`viewN/lim_max/cutoff/shots` 都写死），
  即使键名改对了也拿不到 schema 下发的边界。

#### 为什么删分支而不是"改读对键"

原报告推荐"删掉整个回落分支，强制注入 + fail-fast（学 `initial.js:46-52`）"。
**这条不能照做**：`schema_store.js:1-7` 的模块 docstring 明确写了
`toV1Json`/`stateFromV1` 在未注入时**回退内置常量**（"表示级事实"），
`editor.js:133` 的 docstring 也只声明**两态**。全量 `node --test` 有 76 处
`stateFromJson` 调用走的就是"未注入读常量"路径 —— fail-fast 会让它们全红，
那是**改契约**，不是修 bug。

真正的 bug 是：**多出来的第三态与 docstring 声明的两态契约矛盾**。
所以修法是**删掉中间态**，回归两态：

```js
function tables() {
  if (EDITOR_DERIVED) return EDITOR_DERIVED;
  return { /* ...本地常量（唯一回退）... */ };
}
```

顺带把 `schemaTables` 从 import 里去掉（已无用），
于是"猜已发布表的键名"这个错误类别在 editor.js 里**结构上不可能再发生**。

#### 生产可达性（原报告判断正确）

生产路径 `app.js:849-859` 里 `setEditorSchema(schema)`（`:850`）先于
`publishSchema`（`:854`）且在同一 `try` 内 —— 前者抛则后者不执行，
所以生产上 `EDITOR_DERIVED` 必非空，中间态不可达。它是**潜伏缺陷**：
只有 `tests/editor.test.mjs:1056/1083/1098` 这种"只 publish、不注入 editor"
的混合态能构造出来（`setEditorSchema` 在测试里从未被调用）。

#### 新增守卫（2 条，行为 + 结构）

- `§3.1: 混合态（store 已发布 / editor 未注入）改名仍然正确` —— 按
  `app.js:854-859` 同形发布，断言 op 改名、参数改名、fock drop 三路都正确。
- `§3.1: editor.js 不读未经发布的派生表键（结构守卫）` —— 扫 `editor.js` 源码里
  所有 `s.<key>`（**先去注释**，否则本次修复的历史说明注释自己会命中），
  任何不在 `{uiToOp, uiToParam, fockUiToParam, ops}` 里的键名即失败；
  并断言 `schemaTables` 不再出现。这条锁的是**类别**，以后新加消费口也拦得住。

#### 验证

```
ruff check                  →  All checks passed!
node --test tests/*.test.mjs →  157 pass, 0 fail   （65 → 66 editor，+2 新守卫）
pytest（前端相关 4 文件）     →  78 passed
```

- **变异测试**：把历史那个三键全错的中间态**原样注入**回 `tables()` →
  两条新守卫**立刻红**（64 pass / 2 fail），还原后 66 pass。
  （第一次变异因 CRLF 行尾没匹配上、静默跑在未变异代码上 —— 已重做。）


### 3.2 🟡 三套并行 schema store + 改名表正反手写

**写入方三处**（都由 `app.js:850-859` 驱动）：

| store | 声明 | 写入者 |
| --- | --- | --- |
| `DOC` / `TABLES` | `schema_store.js:10-11` | `app.js:854` **+ `editor.test.mjs:1056,1083,1098`** |
| `EDITOR_SCHEMA` / `EDITOR_DERIVED` | `editor.js:82-83` | 仅 `app.js:850`（测试从不写 → §3.1 的混合态可构造；§3.1 已删掉读这张表的中间态，故此混合态现已无害） |
| `INITIAL_SCHEMA` | `initial.js:15` | `app.js:851`、`editor.test.mjs:822,960,981` |

**改名表重复三份，且正反手写**：

| 位置 | 方向 |
| --- | --- |
| `ops.js:359-372`（`UI_TO_V1_OP` / `UI_TO_V1_PARAM` / `FOCK_UI_TO_V1_PARAM`）+ `:374-378 renames()` | UI→IR |
| `editor.js:75-78,142,145` | IR→UI（手工取反） |
| `ops_schema.js:74-95 deriveParamRenames` | 惰性第三份（仅 `schema_merge.test.mjs:9` 用） |

**修法**：单个 leaf `renames.js` 导出 `{uiToOp, uiToParam, fockUiToParam}` + `invert()`，
从 schema doc 构建；`ops.js` 与 `editor.js` 都读它。配一个 leaf 的 `injectSchema(doc)`，`app.js` 只调一次。

**额外问题**：`editor.test.mjs` 直接改生产单例（`schema_store`），导致测试间顺序耦合。

### 3.3 ✅ `app.js` 0 export，~330 行逻辑 `node --test` 够不到（**大部分已修**）

`app.js` 是 **0 export** 的装配壳 —— 这符合 leaf 纪律。问题在于下列逻辑
本该在 leaf 里，因为没有 export，`node --test` 结构上无法构造。

修复前后（实测）：

| | 修复前 | 修复后 |
| --- | --- | --- |
| `app.js` 行数 | 889 | 851 |
| `app.js` import 的 leaf（去重） | 13 | 16（+3 新 leaf；未删任何 import） |
| `app.js` export | 0 | 0（纪律保持） |
| 三个新 leaf | — | 68 + 60 + 105 行，**各自 0 import** |

**已修（本次）：三个零 DOM 纯函数 leaf，0 生产行为改变。**

| 新 leaf | 搬走的东西 | 新测试 |
| --- | --- | --- |
| `backend_panels.js` | `METER_ROWS` / `BACKEND_PANELS` / `RUN_BODY_EXTENSIONS` / `INITIAL_INPUT_KIND` 四张表 + `panelsFor` / `meterRowPlan` / `runBodyExtensions` / `initialInputKind` 四个查询函数 | `tests/backend_panels.test.mjs`（9 条） |
| `scan_panel.js` | `scanNodeListKey` / `sweepableNodes` / `sweepParamKeys` / `sweepDefaults` / `modesAOptions` / `scanEnabled`（OPS 表以参数注入） | `tests/scan_panel.test.mjs`（9 条） |
| `chart_frame.js` | `themeVars(style, spec)` + 4 张主题色规格表；`gridSegments` / `axisLabelSpecs` / `yFractionScale` | `tests/chart_frame.test.mjs`（12 条） |

**修法与原设想的差异**（三点，都改了结论）：

1. **`meterRows(key)` 改成 `meterRowPlan(keys)`。** 原设想是"键 → 行"的查询函数，
   但那会让**行可见性判断**留在 `app.js` 的循环里。实际收走的是整个渲染计划
   （逐行 `{key, rowId, valueId, label, visible}`），`app.js` 只剩 DOM 汇点。
2. **`heatmap.js` 没做**（见下）。
3. **`chart_frame.js` 的收益与设想不同。** 原以为 `drawFidSvg` 会共用网格/主题；
   实测它**根本不读主题变量**（用 `.bosonic__line` 等 CSS class 着色），与 grid/axis
   无共享面。真正的重复点是 `themeVars`：原先 `drawScanCurve`（app.js）、`drawAxes`
   （app.js）、`drawBars` + `drawJointPair`（fock.js，自带一份同名的局部
   `readThemeVars`）各自实现。`gridSegments` / `axisLabelSpecs` 目前**只有一个消费者**
   —— 抽出来纯粹是为了能直测，不是为了复用；这点写进了 leaf 头注释，避免被误读成
   "为复用而抽象"。

**回退值语义（易错点）**：`--color-accent` 在 scan 路径**无回退**（原来是裸
`.trim()`），在 fock 路径回退 `#2e63d1`；`--color-paper` 同样无回退。收表时逐字
保留，并为此写了专门断言 —— 顺手"统一"回退值会是静默的视觉行为变更。

**未修：`heatmap.js`（推迟，理由不是工作量大，而是护栏性质不同）**。`drawHeatmap`
（65 行）+ `drawAxes` 与**七个模块级缓存**焊死，其行为已被
`tests/lab_heatmap_pixel_probe.mjs` 用**像素哈希**逐点钉住。把缓存搬进工厂函数意味着
重排初始化时序，而像素探针只能告诉你"变了"，不能告诉你"该不该变" —— 风险与收益
不匹配。另外**六个缓存没有 `invalidate()` / reset API**，这仍是真问题，留给下一轮。

注意二者的**部分**改动与"整个函数不搬"并不矛盾，别把它读成自相矛盾：

- `drawAxes` 的**主题读取**已收进 leaf（`AXIS_THEME` + `themeVars`，`getPropertyValue`
  两处 → 一处），这部分零风险、零时序依赖；
- 但 `drawAxes` **函数本身**及其依赖的 `lastLim`（`app.js:187`，与 `drawHeatmap`
  的 `offWRef`/`offN` 等缓存同段）**没动** —— 搬走它必须同时重排缓存时序，
  那正是推迟的原因。

`app.js` 仍是 0 export（leaf 纪律保持）。后端差异的**分支**（`initial.js` 取值合法性、
`ops.js` 序列化、`editor.js` 校验边界）**故意留在原处** —— 那些是表示知识，不是
per-backend 配置表；把 `if (backend === ...)` 全塞进一张表会让表示逻辑反向依赖一张大表。

### 3.4 ✅ `setInitial` 不按 cutoff 夹取（**已修**）

| 位置（修复前） | 事实 |
| --- | --- |
| `editor.js:619-630` `setInitial` | 直接 `next[i] = v`，**无 cutoff 上界** |
| `editor.js:702` / `:726` | 数字框只拿到 `inp.max = (cutoffs[i] ?? 10) - 1` —— **浏览器不会把手工输入夹到 `max`** |
| `editor.js:707` | handler 只拒非整数 / 负数，**放行 9** |
| `fock.js:85-92` `clampInitial` | 唯一真实夹取实现，但只在**拖 cutoff 滑条**那条路上被调（`fock.js:346,399`） |
| `editor.js:781` | 注释却断言"clampInitial 把 initial 夹到 cutoff-1" |
| `cvsim/fock/ir.py:177` | 服务端是**硬拒**：`initial[i]=9 must be in [0, 2)` → 422 |

复现（原报告给的场景）：`cutoff=2` + 手工输入 `9` → 状态 `initial=[9]`、
`staff.js modeLabel` 渲染 `|9⟩`、`/run` 返回 422。

**修法**：原报告建议"`clampInitial` 移到 `initial.js` 导出，`setInitial` 里调，
删 `fock.js` 那份" —— **采纳**。补充原报告没提的一点：必须**限定 fock 分支**。
bosonic 的 initial 项是 `null` / 源名字符串（`initial.js` 语义二分），
无条件过 `clampInitial` 会把源名毁成数字。

```js
initial: state.backend === "fock"
  ? clampInitial(next, state.cutoffs, nm)
  : next,
```

`fock.js` 改为 `import { clampInitial } from "./initial.js"`（它本来就 import
`initial.js` 的语义，无新依赖、无环）。

#### 副作用（已同步处理）

- `tests/fock.test.mjs` 的 `clampInitial` 单测搬到 `editor.test.mjs`
  （导出位置变了），并补 `cutoff=2 → 9 夹成 1` 的缺陷场景用例。
- `tests/test_lab_ui.py:571` 的"纯函数导出未破坏"清单里移除 `clampInitial`
  （它现在属于 `initial.js` 的契约）。

#### 新增守卫（3 条）

- 单测：`clampInitial` 语义（含缺陷场景 `[9],[2] → [1]`）。
- 结构：`clampInitial` 必须由 `initial.js` 导出、`fock.js` 不得留第二份实现、
  且必须从 `initial.js` import。
- 结构：`setInitial` 体内必须出现 `clampInitial(`，且必须带
  `backend === "fock"` 限定。

#### 验证：真实浏览器探针（行为级）

新增 `tests/lab_initial_clamp_probe.mjs`（Edge headless + 真实 `uvicorn`，
与 `lab_interaction_probe.mjs` 同法）。注入 `cutoff=2` 的 fock circuit，
往 mode-0 初始态输入框**真的敲 9**，然后读回状态 JSON、mode 标签、
以及 `/run` 的 HTTP 状态：

```
PASS  premise: initial input advertises max=cutoff-1=1 — max="1" value="0"
PASS  state JSON carries initial 1 (clamped to cutoff-1), never 9 — json.initial=[1] cutoff=2
PASS  mode label shows |1⟩ and never |9⟩ — labels=["mode 0 · |1⟩"]
PASS  input box snaps back to the clamped value — input.value="1"
PASS  no /run request was rejected — runs=[{"/run",200},{"/run",200}] state="ok"
```

**变异测试（决定性）**：把 clamp 删回原样，同一个探针立刻复现原缺陷 ——

```
FAIL  state JSON carries initial 1 ... — json.initial=[9] cutoff=2
FAIL  mode label shows |1⟩ and never |9⟩ — labels=["mode 0 · |9⟩"] [|9⟩ RENDERED]
FAIL  input box snaps back ... — input.value="9"
FAIL  no /run request was rejected — runs=[...,{"/run",422}]
      status="422 · initial[0]=9 must be in [0, 2)" state="error"
```

即原报告描述的"422 + `|9⟩`"**逐字复现**，证明探针测的是真缺陷而非同义反复。

### 3.5 🟡 两个 GET 绕过 `requestLab`，"信封收敛"名不副实

- `app.js:844` `await (await fetch("/schema")).json()` —— 裸 fetch，无 `ok` 检查
- `app.js:867` `void fetch("/health")` —— 裸 fetch

`requestLab`（`request.js:61`）**在构造上只能 POST**（`request.js:83` 硬编码 `method: "POST"`），
所以 `request.js:2-5` 声称的"5 处重复信封收敛"不成立 —— 它收敛不了 GET。

**修法**：`requestLab` 收 `{method, path}`（或加 `getLab(path, opts)`），`app.js:844/867` 走它，
于是 `reportError`（`app.js:73-77`）成为唯一错误渲染口。

### 3.6 🟢 `app.js` import 期抓 22 个 DOM 句柄 + 全局 keydown

- `app.js:24-63`：`const $ = (id) => document.getElementById(id)` 后，顶层 22 个
  `const x = $(...)` **在 import 时求值**。任一 id 漂移 → `null` → 后续才 TypeError（消息不可读）。
  对照 `editor.js:342-354`、`fock.js:262-280` 都是在 `init` 内查询并用 `?.`。
- `editor.js:384`：`document.addEventListener("keydown", …)` 在一个签名只有 `(root, hooks)` 的函数里
  注册**全局且永不解绑**的监听器。真实依赖 `document` 没被注入 → 这条路径**构造上不可单测**，
  违反 leaf 纪律"环境依赖由调用方注入"。

**修法**：句柄改成 `init()` 内构造的惰性 `dom` 表；`initEditor(root, hooks, deps)` 注入 `{doc, win}`。

### 3.7 🟡 `/schema` 已下发 `sweepable`，前端零消费

- 后端：`cvsim/lab/schema.py:142` 的 `extensions.sweepable` ← `schema.py:125-133` `SWEEPABLE_PARAMS`
- 前端：**没有任何文件读它**；反而在 `app.js:567,578,615,703` 重推 5 次
  `Array.isArray(d.sweep)`，外加 `staff.js:449`
- `ops.js:6-7` 的注释自认"mirrors schema.py SWEEPABLE_PARAMS"

同一声明两个事实源，正是本项目在 `schema.py:100-104` 等处反复消灭的镜像反模式。

**修法**：前端改读派生自 `/schema` 的 `sweepable` 表，`ops.js` 的 `sweep` 字段降级为纯 UI 滑块刻度提示。

### 3.8 🟢 其他重复构造与死代码

**重复**：

- `<option>` 构造 **6 份**：`app.js:321,582,602,626`、`editor.js:653`、`fock.js:301`
- 主题变量读取 **3 份**：`app.js:187-189`、`app.js:665-668`、`fock.js:124-129`
- cutoff 默认值 `10` **硬编码 17 处**：`editor.js:20,56,491,599,621,708,732`、
  `fock.js:89,292,314,315,334,340,342,357`、`ops.js:441`
- per-mode 数组 pad：`editor.js:24-27 padTo` vs `fock.js:342` 内联 vs `editor.js:491,599,621`
  → 建议 leaf `cutoffs.js`：`DEFAULT_CUTOFF` / `padCutoffs` / `uniformCutoffs` / `clampInitialToCutoff` / `cutoffBounds`

**死代码**：

- `lastGood`（`editor.js:360,747,769,800`）—— 只写不读，唯一"读"在注释 `:766`；
  frozen-graph 策略实际由 `:764-767` 的提前 `return` 实现
- `ops.js:351-355 updateMode` —— 无生产调用者（仅 `editor.test.mjs:370-372`）
- `ops.js:200-208 xOf` / `modeKeyOf` —— 导出但仅内部 `:212` 用
- `colormap.js:34-40 validateWignerGrid` / `:44-48 wignerScale` —— 被 `:56 inspectWignerGrid` 取代，
  仅靠 `colormap.test.mjs:47-77` 续命
- `svg_kit.js:8 SVG_NS` —— 无调用者
- `editor.js:91-93 currentEditorSchema` / `initial.js:22-24 currentInitialSchema` /
  `schema_store.js:28-30 schemaDoc` —— **生产与测试都零调用者**
- `ops_schema.js:67-68 __extensions` / `__initial` —— 仅 `schema_merge.test.mjs:91-93` 读；
  `editor.js:96-131` 自己另派生一份
- `app.js:238-243 METER_ROWS[].label` —— 从不读取（`renderMetersPanel` `app.js:251-259` 只用 `row.value`）；
  标签实际活在 `index.html:106-109`
- `app.js:882` 的 `"fidelity-btn"` —— **该 id 不存在**（`index.html:174` 只有 `bos-fidelity-btn`）；
  靠 `if (el)` 守卫无害，但 `test_lab_ui.py:665` 还按字符串断言它

**已退役 op 检查**（`vacuum`/`tmsv`/`coherent`）：`static/*.js` 里**无活引用**，残留命中都是回归守卫
（`editor.test.mjs:45-47,437,749,1071-1073`、`lab_staff_probe.mjs:166,385-386`）—— **保留**。
例外：`steps_slider.test.mjs:66` 拿 `"tmsv"` 当任意 fixture 字符串，可顺手改成 `"two_mode_squeeze"`（纯美化）。
注意 `test_lab_schema.py:53-54,112` 的 `"vacuum"` 是**bosonic initial 的活键名**，是另一个概念，不动。

**渲染缺陷**：

- `renderBosonic`（`app.js:339-345`）不重置 `#rbar-block`。`app.js:278` 只在 gaussian 路径
  `hidden = false`，而 `BACKEND_PANELS.bosonic` 的 `"wigner-side": true`（`app.js:456`）
  → gaussian 切 bosonic 后残留上一模式的均值表，配着新写的 `nmode-tag`（`app.js:342`）。
  fock 因 `"wigner-side": false`（`app.js:455`）被掩盖。

**零覆盖路径**：保存 / 加载（`app.js:793-831`）—— **无探针、无 pytest、无 node 测试**。
另有主题兜底色（`app.js:188,665-668`、`fock.js:124-129`）同样零覆盖。

**`svg_kit.js` 的边界声明与实现不符**：`svg_kit.js:3` 自称"leaf 纪律中唯一允许的 DOM 边界"，
但 `:12` 的 `el()` 在调用时解引用**全局 `document`**，而不是作为参数接收。
对照 `request.js:66` 的 `fetchImpl = globalThis.fetch` 是**可覆盖的**。
建议 `el(tag, attrs, doc = document)`，或把 `el` 拆到独立 `svg_dom.js`，让 `svg_kit.js` 成为真零 DOM leaf。

**`index.html` 脚本耦合**：`index.html:231` 只有一个 `<script type="module" src="app.js">`，
**无脚本顺序风险**（历史担忧不成立）。真实的隐式耦合是 (a) §3.6 的 22 个 import 期 id，
(b) `test_lab_ui.py:56-82` 从 60+ 个 id 里白名单 22 个，(c) `index.html:59-61` 的注释耦合到
`staff.js` 的 `replaceChildren()`。

---

## §4 测试与工具链

### 4.1 ✅ CI lint 在 `master` 上原本是红的（**已修复**）

修复前实测：

```
tests\test_lab_ui.py:664:101: E501 Line too long (101 > 100)
Found 1 error.
```

CI 的 `lint` 任务（`.github/workflows/ci.yml:20-27`）跑的是**不带路径**的 `ruff check`，
会扫到 `tests/`。lint 与 pytest 是独立任务，所以 lint 红与测试无关。

**已修**：把 `:664` 那个 tuple 折成两行。

```python
    for bid in (
        "run-btn", "sample-btn", "scan-btn", "save-btn", "fidelity-btn", "bos-fidelity-btn",
    ):
        assert f'"{bid}"' in init, f"失败禁用清单缺 {bid}"
```

**验证**（`tests/test_lab_ui.py` 单独跑，改动只涉及换行，断言集合与顺序未变）：

```
pytest tests/test_lab_ui.py  →  31 passed
ruff check                   →  All checks passed!
mypy cvsim/                  →  Success: no issues found in 62 source files
pytest （全量）              →  1508 passed, 12 skipped
```

### 4.2 ✅ CI 从不运行 9 个 `*.test.mjs`（**已修**）

`ci.yml` 原本六个任务：`lint` / `type-check` / `test` / `api-freeze` / `benchmark` / `gbs`
—— **无 node 步骤**（`grep node .github/workflows/ci.yml` → 0 命中）。

叠加 `pyproject.toml` 的 `testpaths = ["tests"]` + `python_files = ["test_*.py"]`
（`.mjs` 对 pytest 不可见）—— 整个前端 leaf 契约层是**本地手工仪式**。本地基线：**155 pass, 0 fail**。

**关于"目录模式"的实测补充**：初版报告说"`node --test` 的目录模式也不收 `.mjs`"。
这次在 node v24.11.0 上实测得更准确 —— 目录模式不是"不收"，而是**直接报错**：

```
$ node --test tests/
Error: Cannot find module 'E:\...\cv-photonic-notes\tests'   # 1 test, 1 fail
```

所以原报告"必须显式列文件"的结论正确，只是原因更硬：目录模式**根本跑不起来**。

**已实施的修复**（`.github/workflows/ci.yml` 新增第七个任务）：

```yaml
frontend:
  name: Frontend leaf tests (node --test)
  runs-on: ubuntu-latest
  timeout-minutes: 5
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: "22"
    - run: node --test tests/*.test.mjs
```

两个设计决定：

- **用 glob 而不是硬编码文件名**。原报告的修法是"显式列 9 个文件"，
  但那样每加一个 leaf 测试都要改 workflow——**守卫漏掉新测试**正是要防的失败模式。
  shell 会先把 `tests/*.test.mjs` 展开成文件列表再交给 node（已实测两种形态都跑 189 pass），
  所以新测试**零改动自动纳入**。（CI 的 `run:` 走 bash，Windows 的 pwsh 行为不影响。）
  实测验证：§3.3 新增三个 `*.test.mjs` 后无任何 workflow 改动即被 CI 覆盖。
- **`node-version: "22"`（LTS）**。仓库原本不 pin node 版本，而 leaf 测试/其依赖的
  `static/*.js` 用了 `structuredClone`（Node 17+）与 `??=`（Node 15+）。
  pin 住避免"某天 ubuntu-latest 的 node 变了导致前端契约层莫名红"。

**配套守卫 `tests/test_frontend_leaf_suite.py`**（5 个测试，纯 stdlib，不引 `pyyaml`——
它不在 `dev` extra 里，CI 装不到）：把"CI 接线"本身变成机器检查。防两种静默腐烂：

1. **CI 断线** —— 有人删/改任务或命令；断言 `ci.yml` 里存在一条**非注释**的
   `run: node --test tests/*.test.mjs`。
2. **测试没被收进去** —— 新增的 leaf 测试放到 glob 够不到的**子目录**
   （`tests/frontend/x.test.mjs`）→ 文件在，但永不运行。断言所有
   `*.test.mjs` 的父目录**恰好**是 `tests/`。

外加两条防空转：每个文件必须 `import "node:test"`（否则零测试、node 退出 0 静默通过）
且必须 import 一个 `../cvsim/lab/static/*.js` leaf；以及 leaf 测试数量 == **12**
（§3.3 后由 9 增至 12；数字变了就强制回头改文档，而不是默默漂移）。

**变异测试**（确认守卫不是摆设）：逐个制造 6 种腐烂 ——
命令被替换 / glob 被改 / 步骤被注释掉 / 测试挪进子目录 / 放一个零测试的 `.test.mjs` /
加第 13 个测试 —— **6 种全部被抓**（分别红 2/2/1/2/2/1 个用例）；未变异的对照跑绿。
（§3.3 实测：新增三个 leaf 测试文件后，计数守卫如期报 `expected 9 ... found 12`，
确认它在 CI 里是真的门禁而不是常量。）

**额外验证**：故意放一个 `assert.equal(1, 2)` 的测试 → `node --test` **rc=1**，
证明这条 CI 任务真的有门禁作用（不是永远绿的装饰）。

### 4.3 ✅ `tests/` 扁平目录混四类东西（**已修**）

| 类别 | 数量 | 命名 | 跑法 |
| --- | --- | --- | --- |
| pytest | 110 | `test_*.py` | `pytest tests/` |
| node 单测 | 12 | `*.test.mjs` | `node --test <文件>…`（目录模式不收） |
| CDP 浏览器探针 | 11 | `lab_*_probe.mjs` + `_debug_probe.mjs` | `node tests/…mjs`（需浏览器 + uvicorn） |
| **非测试** | 2 | `probes/_adversarial_*_review.py` | 手工 |

#### 已实施

1. **两个手工脚本收进 `tests/probes/`**（原在 `tests/` 根，与 110 个真测试混住）。
   已核实它们**不是**已收集 `test_adversarial_channel.py` 的副本（MD5 不同，diff 824 行），
   且 `python_files = ["test_*.py"]` 保证 pytest 依旧不收集它们。两处 docstring 的
   run 命令同步改了路径。
2. **补 `tests/README.md`**（此前根 / `cvsim` / `benchmarks` / `scripts` / `tutorials`
   都有，唯独 `tests/` 没有）。内容：四类跑法矩阵、三层分工（ADR-0009）、
   探针环境变量表、三套 golden 的重生成命令、marker 的定位说明、
   `.venv` 环境一致性警告。

#### 未做（有意）

`tests/{unit,integration,golden,frontend,probes}/` 全量拆分**没做**。理由：
`probes/` 已把唯一真异类收走；剩下三类靠**命名前缀**已经能区分（`test_*.py` /
`*.test.mjs` / `lab_*_probe.mjs`），而全拆分要动 110 个文件的路径、连带 CI 的
`node --test tests/*.test.mjs` glob 与 `test_frontend_leaf_suite.py` 的数量守卫 ——
收益是"目录更整齐"，成本是大面积 churn。**若将来做，必须同步改那两处。**

### 4.4 ✅ 探针的平台假设使其在 CI 上永不可跑（**已修**）

原状：12 个探针硬编码
`"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"`
与 `spawn("<cwd>/.venv/Scripts/uvicorn.exe")`，**无 `process.platform` 分支、
无环境变量覆盖**；端口手工分且**两对撞车**（8860+9224、8771+9229）。

#### 已实施

新增 `tests/probe_env.mjs`，只做一件事：把「浏览器在哪 / uvicorn 在哪 / 用哪个端口」
从代码挪到环境变量 + 平台默认值。**探针逻辑零改动**。

| 变量 | 作用 | 默认 |
| --- | --- | --- |
| `EDGE_PATH` | 浏览器可执行文件 | 按 `process.platform`：Windows 探两个常见安装位置（用 `existsSync` 挑）/ macOS 的 `Microsoft Edge.app` / Linux 走 PATH 的 `microsoft-edge`（也认 `CHROME_PATH`） |
| `UVICORN` | uvicorn 可执行文件 | `.venv/Scripts/uvicorn.exe`（win32）或 `.venv/bin/uvicorn` |
| `PROBE_PORT` | lab server 端口 | 各探针**自己的历史默认值**（8765–8773 / 8860） |
| `PROBE_CDP_PORT` | CDP 调试端口 | 各探针自己的历史默认值（9223–9231） |

端口默认值**刻意保留各探针原值**而非统一重编 —— 改了默认值就等于改手跑习惯，
而这与"修平台假设"无关。设了环境变量即可并行跑。

profile 目录（原先 `process.cwd() + "/.probe-*"`，往仓库根写）改走
`userDataDir()` → 系统临时目录。

12 个探针全部改接：`_debug_probe` / `lab_bosonic` / `lab_control_height` /
`lab_heatmap_pixel` / `lab_heatmap_rect` / `lab_initial_clamp` / `lab_interaction` /
`lab_render_perf` / `lab_scan` / `lab_staff` / `lab_undo` / `lab_wigner_layout`。

验证：
- `node --check` 全部 25 个 `.mjs` 语法通过。
- **实测跑通一个真探针**（不是只做静态检查）：`node tests/lab_initial_clamp_probe.mjs`
  → 真起 uvicorn + headless Edge + CDP，5/5 check PASS，exit 0。这一步同时证明
  `probe_env.mjs` 的默认值在本机等价于原先的硬编码值。

#### 未做（有意）

**没让探针在 ubuntu CI 上真跑。** 那需要在 CI 装浏览器 + 加 job，而探针是
"本机像素/装配验证"性质的工具（ADR-0009 第 2 层），不是必须的 CI 门。
本次只消除"平台假设把它锁死在 Windows"这一条 —— 现在**可以**在别的平台跑，
只是 CI 里还没接。

端口改成从环境变量取或随机分配。

> 注：探针 profile 缓存目录（原 `.probe-*` 那批）**已被清理**，AGENTS.md 也已新增纪律
> "浏览器探针生成的临时的 .probe* 文件使用完了就要删除"。此项仅剩"平台可移植性"未解决。

### 4.6 ✅ `tests/test_lab_ui.py` 是"读源码字符串"测试（**已修：标注分层 + 退化为接线断言**）

实测（基线 `1e207cd`，文件 777 行）：31 个测试中 **24 个**函数体含 `read_text()`，
**1 个**（`test_default_scene_to_v1_byte_frozen`）shell out 到 node 比对逐字 golden 字符串 ——
合计 **25/31** 依赖源码文本。真正的纯行为测试只有 **6 个**：`test_a3_logneg_freeze`、
`test_assets_served`、`test_default_scene_runs`、`test_index_served`、`test_key_elements_present`、
`test_view_bounds_enforced`。

源码字符串断言的例子：

- `:319-328` 断言 `"function syncChrome()" in js`，再 `js.split("function render() {")`
- `:395` 附近断言整条语句逐字：`"if (canvas.width !== pw) canvas.width = pw;"`
- `:667-670` 断言 `fetch("/health")` 相对 `editor.render()` 的**源码位置**

后果：JS 里改个局部变量名 → pytest 红；真实行为坏了 → 可能照样绿。
这正是 `docs/adr/0009-frontend-leaf-testing.md` 引述并要消灭的形态。

**修法（定案：分层标注，而非删掉重写）**。逐条删除不可行：其中相当一部分守的是
**跨文件接线边**或**"某次视觉回归已被实测否决，不得重新引入"**，这两类既不是单个 leaf
的行为、也没法写成"给定输入 → 给定输出"。故采取：

1. **文件头声明三层分工**：leaf 行为 → `tests/*.test.mjs`（`node --test`）；
   整页行为 → `tests/lab_*_probe.mjs`（headless Edge + CDP）；
   **源码形状 → 此处**。并写明判定标准："只有当被测主体**确实就是源码文本**时才留在这里；
   凡能写成『给定输入，函数返回这个』的，都属于 leaf 层。"
2. **两张登记表**：`SHAPE_GUARDS`（每条附一句"为什么它确实属于形状层"）与
   `BEHAVIOUR_TESTS`。
3. **meta-guard** `test_shape_guards_are_declared_not_silently_behavioural`：
   本文件每个 `test_*` 必须出现在恰好一张表里（漏登记 → 红；同时在两张表 → 红；
   登记了却已删除 → 红），且 `SHAPE_GUARDS` 里至少 24 条真的在读前端源码 ——
   防止分类本身腐化。已变异验证（删一行登记 → 红）。
4. **行为主体已迁走的，原测试退化为只断言接线边**（本节的主要实际收益）：

   | 原测试 | 行为主体去哪了 | 现在断言什么 |
   | --- | --- | --- |
   | `test_scan_dirty_key_is_node_identity_not_array_ref` | `scan_panel.js` `scanNodeListKey` → `tests/scan_panel.test.mjs`（含"重建数组同键"这条原本想守的性质） | `app.js` 仍把 `state` + `OPS` 交给 leaf，且没再抄一份 `${n.id}:${n.op}` |
   | `test_fock_theme_vars_read_in_one_pass` | `chart_frame.js` `themeVars` + 规格表 → `tests/chart_frame.test.mjs`（含回退值逐字断言） | `fock.js` 仍只有一个 `themeVarsOf` DOM 边界、恰好一处 `getComputedStyle` |

5. **离线 URL 守卫顺带加强**：原来只扫 `index.html/tokens.css/style.css/app.js` 四个硬编码
   名字 —— 新抽出的 leaf 会被服务、却永不进入扫描。现改为**按 import 图从 index.html
   发现**全部被服务的前端文件（`_served_frontend_files()`），新 leaf 自动纳入。
   已变异验证：往 `backend_panels.js` 塞一个 `https://` 即红。

**仍保留的 27 条形状守卫**按主题分四类：服务/存在性（4）、跨文件接线边（8）、
"已否决的改动不得回归"反向守卫（5）、装配与时序形状（9）。
### 4.7 🟡 30 处测试 import cvsim 私有名（AST 实测，17 个文件）

`__all__` 被文档定义为公开面（`docs/api-stability.md` §2.1/§2.3："任何 `_` 开头的名字 = Private，
无稳定性承诺"），但 pytest 直接 import 私有名。用 `ast` 静态扫描 `tests/test_*.py` 的 `ImportFrom`
（`module.startswith("cvsim")` 且 `name.startswith("_")`）实测：**30 处，17 个文件**。

| 文件:行 | 私有名 |
| --- | --- |
| `test_analyse.py:19` | `cvsim.gaussian.analyse._as_cov`, `._bosonic_g` |
| `test_b3_bosonic_homodyne_exact.py:36` | `cvsim.fock.observables._amps_for_phi`, `._ho_basis_x` |
| `test_b4_bosonic_reconciliation.py:42` | 同上两个 |
| `test_b6_bosonic_gui.py:23` | `cvsim.bosonic.gkp._gauss_overlap`, `._gauss_overlap_two_V` |
| `test_b7_kernel_log_domain.py:89` | `cvsim.bosonic.analyse._K_pair` |
| `test_bosonic_analyse_complex.py:27,82` | `cvsim.bosonic.cat._cat4` |
| `test_bosonic_gkp_gram.py:9` | `cvsim.bosonic.gkp._gauss_overlap` |
| `test_compile.py:8` | `cvsim.gaussian.compile._compile_segments`, `._instantiate`, `._run_op` |
| `test_fock_ad_f4.py:18` | `cvsim.fock_ad._cat_amps`, `._loss_superop` |
| `test_fock_circuit_f3.py:109` | `cvsim.fock.circuit._bs_U` |
| `test_fock_condition.py:16` | `cvsim.fock.observables._x_phi_matrix` |
| `test_fock_gates_f1.py:166` | `cvsim.fock.gates._squeeze_U` |
| `test_fock_homodyne.py:110` | `cvsim.fock.observables._pdf_from_amps` |
| `test_fock_measure_f2.py:137,149` | `cvsim.fock.observables._q_function` |
| `test_fock_squeeze_phi.py:23,80` | `cvsim.fock.gates._squeeze_U` |
| `test_lab_scan_extract.py:80` | `cvsim.lab.ir._num`, `._require` |
| `test_whitelist_derived_drill.py:24` | `cvsim.lab.schema._PKG_SCHEMAS`, `._UI_HIDDEN`, `._derive_whitelist` |

另有 1 处形态**正确**、不应改：`test_lab_backend_symmetry.py:307` 把 `_wigner_mode_guard_fail`
当作**字符串**列入白名单（不是在 import 私有名）。

**真实边界 bug 在于不对称**：`tests/test_public_api.py:96-119` 的 `test_examples_phase1_imports_public_only`
用 AST 强制"不许导私有"，但**只覆盖 `examples/phase1_exit_demo.py` 一个文件**；`tests/` 自己反而没人管。
`benchmarks/benchmark_m100.py:25` 也导了 `cvsim.gaussian.compile._run_op`
（`benchmarks/README.md:26-30` 已记录为已知债）。

**修法**：逐个名字决定 —— 提升进 `__all__`，或把测试改到 `__all__` 可见的接缝，或加统一 marker 把债变成可计数。
并把 `test_public_api.py` 的 AST 守卫**扩展到 `tests/` + `benchmarks/` + `tools/`**。
注意 `test_compile.py:8`（3 个名字）与 `test_whitelist_derived_drill.py:24`（3 个名字）
是"整条测试都建立在私有面上"的典型，优先处理。

### 4.8 ✅ `pyproject.toml` / CI 配置缺口（**已修**）

原报告的四条，逐条核实后有**两条不准确**：

| 项 | 原报告说法 | 实测 |
| --- | --- | --- |
| coverage | 无 `fail_under` → 覆盖率掉到 0 也不红 | ✅ **准确** |
| `omit` 副作用 | `omit=["cvsim/demos/*"]` 把 `m4_cross_rep.py` 也排除了，而 `tests/test_m4_cross_rep.py:4` 唯一跑的就是它 | ✅ **准确** |
| markers | "`phaseB9`/`phaseB10` 声明了从未使用" | ⚠️ **说反了一半**。实际：`phaseB7` 声明了**零文件**用（`test_b7_kernel_log_domain.py:22` 误标成 `phaseB6`）；`phaseB9`/`phaseB10` 的**测试文件存在但漏打 marker**（`test_b9_bosonic_pnr.py`、`test_b10_bosonic_pnr_joint.py` 全文无 `pytestmark`，B9 连 `import pytest` 都没有）。结论仍是"marker 体系有问题"，但病因是**漏标 + 误标**，不是"声明了没人用" |
| mypy | `exclude=["tests/"]` 与 `module="tests.*" ignore_errors=true` 并存 → 后者死配置 | ✅ **准确** |
| `conftest.py` | 12 个符号零引用 | ✅ **准确**（已逐符号复测） |

#### 已实施

1. **`fail_under = 90`。** 先装 `pytest-cov` 量出真实基线（修好 `omit` 之后）：
   **6095 stmts / 381 missed / 2258 branch / 283 partial → 91.69%**。
   门设 90，留约 1.7 点余量给重构抖动，但不允许无声下滑。
   **变异验证过门真的会红**：只跑 `tests/test_dispatch.py` → 34.29% → `FAIL Required test coverage of 90.0% not reached`，exit 1。
2. **修 `omit` 的覆盖面。** 通配符 `cvsim/demos/*` 换成逐一列出四个**真的**无人执行的
   demo 脚本，把 `m4_cross_rep.py` 放回统计（它被 `tests/test_m4_cross_rep.py` 唯一地跑着）。
   通配符盖住被测代码，比不设 omit 更坏 —— 它让覆盖率数字**偏高且无从察觉**。
3. **删死 mypy override。** `exclude` 已覆盖，那条 override 永远匹配不到文件。
   留一行注释说明为何删（免得后人"补回配置对称性"）。
4. **`conftest.py` 169 → 101 行。** 删 12 个零引用符号：`vacuum_1/2/3` fixture、
   六个 `*_VALUES` 表（`SQUEEZING_`/`NBAR_`/`ALPHA_`/`PHASE_`/`TRANSMITTANCE_`/`NMODE_`）、
   `assert_allclose_weak`/`assert_physical`/`assert_pure`、从未被请求的 `rng` fixture
   （0 个 `def test_*(rng)`；测试直接 `default_rng()`）、以及只被 `assert_allclose_weak`
   用的 `TOL_LOOSE`。连带 `from cvsim.gaussian import GaussianState` 也成了未用 import，
   一并删。module docstring 里补了**为什么删**（死 fixture 比没有 fixture 更坏：
   它暗示了一份并不存在的覆盖）。
   保留的：`backend` fixture（279 处用）、`TOL`（34 处）、`assert_allclose`（476 处）、
   三个 LabResult 契约 helper（`gaussian_V` 16 / `gaussian_rbar` 11 / `wigner_result` 9）。
5. **marker 收口。** `test_b7_kernel_log_domain.py` 的 `phaseB6` → `phaseB7`；
   给 B9/B10 两个文件补 `import pytest` + `pytestmark`。
   验证：`pytest tests/test_b9_bosonic_pnr.py tests/test_b10_bosonic_pnr_joint.py -m phaseB9`
   → **6 passed, 11 deselected**（此前是 17 deselected —— 一个都选不中）。
   `tests/README.md` 写明"marker 是选择器，不是执行门"（CI 里确实没有 `-m phaseB*` 任务，
   但那是**设计如此**：全套每次跑，marker 只供本地聚焦 —— 这一条**不作为缺陷处理**）。

#### 未做（有意）

`tools/` 仍在 ruff `extend-exclude` 里（7 个 `probe_*.py` + `gen_sf_golden.py` 既不 lint
也不执行）。这是**刻意的**：那些是一次性对照脚本，按库代码标准 lint 会产生大量
无关噪声（`tutorials` 同理，169 处错全在此带）。若将来要收，应单独成票并先实测噪声量。

### 4.9 🟡 golden 文件的脆弱性（两类，性质不同）

**逐字节类（环境脆弱）**：

- `tests/test_lab_golden.py:53` `assert body == golden`（完整嵌套 dict 相等）覆盖 9 个 JSON
- `tests/test_lab_ui.py:303` 附近 `assert proc.stdout.strip() == golden`（node 输出整串 JSON）
- `tests/test_lab_ui.py:280-289` `test_default_scene_to_v1_byte_frozen` 钉住 JSON **文本**，于是 `toV1Json` 的键序被冻结

这些 golden 里的浮点值来自 numpy RNG 流（`tests/golden/capture_golden.py:52,71,73` 播种），
而 `uv.lock` 里 **numpy 按 Python 版本分叉**（3.10→2.2.6 / 3.11→2.4.6 / ≥3.12→2.5.1），
CI 跑 4 个 Python 版本 → **它们根本不是一个 numpy**，golden 只在捕获它的那个版本上可靠。

**1-ulp 类**：`tests/test_sf_golden_f6.py:40` 用 `atol=1e-9` 逐元素比复数密度矩阵，
但 npz 由 SF/thewalrus 0.23/0.22 生成（`:104-105` 断言元数据）→ 锁死在一个**未 pin 的外部包**上。
`tests/test_observables_batch.py:94-107` 硬编码 8 个采样值（`atol=1e-8`，依赖 RNG 流）。

本机（py3.13.5 / numpy 2.5.1）实测这 31 个测试**全绿** —— 但那只证明"这台机器绿"，不证明可移植。

**重生成路径不统一（三套）**：

| 产物 | 命令 | 问题 |
| --- | --- | --- |
| API golden（9 个 JSON） | `python tests/golden/capture_golden.py` | docstring `:5` 声称"Re-run with `--check`"，但**代码里没有 argv 处理**，`--check` 根本不存在（检查逻辑实际在 `test_lab_golden.py`） |
| SF golden（npz） | `tools/gen_sf_golden.py`（需 StrawberryFields venv） | 有自检 `max\|d\| < 1e-8` 才写（`:269-278`），较稳 |
| 像素基线 | `node tests/lab_heatmap_pixel_probe.mjs --write` | 写被跟踪的 `tests/lab_heatmap_pixels.json` |

**修法**：(a) 删掉或实现那个不存在的 `--check` 声明；(b) API golden 改成**数值容差**比对而非 `body == golden`；
(c) CI 里把 golden 任务 pin 到单一 Python/numpy；(d) 把三条重生成命令收进一份 `tests/README.md`。

### 4.10 ✅ 死/孤儿产物与 gitignore 漏洞（**已修一项，其余记录**）

| 项 | 状态 | 说明 |
| --- | --- | --- |
| `lab_server.err.log.crash` | ✅ **已修** | `.gitignore` 由 `lab_server*.log` 改 `lab_server*.log*`；`git check-ignore -v lab_server.err.log.crash` **现命中** `.gitignore:56`。两个 crash 文件 + 4 个陈旧 `lab_server{,_err,.err,.out}.log`（约 460 KB）已删 |
| 根因 | **未修** | 这些日志是 lab server 的运行时产物，正确修法是让 server 写到 `os.tmpdir()`，而不是靠 ignore 兜住。ignore 只解决"仓库变脏"，没解决"运行时往仓库根拉屎" |
| `.control-height.png` | 已忽略，**未修** | `lab_control_height_probe.mjs` 每次运行都往仓库根写 → 应指向 `$TEMP`（本次探针改造只动了 profile 目录与端口，没动这个输出路径） |
| `benchmarks/latest.json` | 被跟踪，**未修** | 每次 `benchmark_m100.py` 都重写，CI benchmark 任务一跑就把仓库弄脏 |
| `tools/dsh-trellis-breadcrumb/` | 被跟踪，**未修** | 一个 Node 包（依赖 `@deepseek-ai/dsh-llm`），仓库内无 `node_modules`，`test.mjs` 在此跑不了 —— 外来构建产物混进 Python 物理仓库 |

### 4.11 🟢 其他

- **`docs/adr/` 缺 0013**：现有 0001–0012 + 0014（编号 0013 完全不存在，全库零引用）→ 编号空洞，建议补一份或加注说明
- **ADR-0001 文本已过期**：ADR-0001 #5 的拆分触发器（"文件 >~800 行 / circuit_v1 schema 出现"）**两条都已触发**。
  `cvsim/lab/ir.py` 现为 **333 行**（已拆出 `gaussian_backend.py` / `fock_backend.py` / `bosonic_backend.py` /
  `scan.py` / `dispatch.py`），文件拆分那一半已解决 → ADR 正文该回填实测状态
- **`.scratch` 悬空引用**：三份 `ir.py` 的 docstring 仍引用 `.scratch/schema-single-source/spec.md`
  （`cvsim/gaussian/ir.py:35,47` 等）。该文件现已恢复在位，所以引用**不是悬空的**；
  但若将来清理 `.scratch`，这三处需同步
- **`examples/` 与 `cvsim/demos/` 绕过公开导入**：`docs/api-stability.md` §7 要求"demo/tutorial 只用公开导入"，
  但 `examples/phase1_exit_demo.py:28-31` 直接 import `cvsim.gaussian.channels/gates/observables/state` 子模块；
  `cvsim/demos/m2_fock_cutoff_scan.py:8`、`cvsim/demos/user_acceptance.py:37-38` 同样。
  `test_public_api.py` 的守卫只查**私有名**（下划线开头），所以这些非下划线子模块导入全部漏网
- **`scripts/_tw_gauss_checks.py` / `_tw_fidelity_src.py`**：vendored Xanadu 源码（Apache-2.0，带版权头），
  下划线前缀 + ruff 排除，用途除了读代码无从得知（`scripts/README.md` 有说明）
- **`tests/test_gkp_tutorial.py:64-78`** `test_notebook_build_is_stable` 跑
  `subprocess.run([sys.executable, "tutorials/_build_06.py"])`，该脚本**重写被跟踪的**
  `tutorials/06_gkp_feedforward.ipynb`（`_build_06.py:194`），然后只断言 `nbformat == 4` 和 cell 数 ——
  **一个会悄悄改被跟踪产物、且永远不可能失败的测试**
- **`tests/golden/__pycache__/`** 含 3 个 Python 版本的 `.pyc`（3.11/3.13/3.14）→ 证明 `capture_golden.py`
  被多解释器导入过（已忽略，无害）
