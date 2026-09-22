# tests/ — 跑法矩阵（2026-09-18 审计 §4.3 补）

这个目录混着**四类性质完全不同**的东西。跑法不对，测试就是绿的假象。
按你要验证什么，选对应那一行。

| 类别 | 数量 | 命名 | 跑法 | CI |
| --- | --- | --- | --- | --- |
| pytest 单测/集成 | 110 | `test_*.py` | `.venv/Scripts/python.exe -m pytest tests/ -q` | ✅ 4 个 Python 版本 |
| node leaf 契约层 | 12 | `*.test.mjs` | `node --test tests/*.test.mjs` | ✅ `frontend` job |
| CDP 浏览器探针 | 11 | `lab_*_probe.mjs` | `node tests/lab_xxx_probe.mjs` | ❌ 需真实浏览器 |
| 调试探针 | 1 | `_debug_probe.mjs` | `node tests/_debug_probe.mjs` | ❌ |
| 手工审查脚本 | 2 | `probes/_adversarial_*_review.py` | `PYTHONPATH=. .venv/Scripts/python.exe tests/probes/_adversarial_channel_review.py` | ❌ pytest 不收集 |

**关键坑：`node --test tests/` 跑不了。** 目录模式不支持 `.mjs`，会硬报
`Error: Cannot find module '...\tests'`。**必须用 glob** `tests/*.test.mjs`
（由 shell 展开，所以新增 leaf 测试不用改命令）。

## 分层：三层，各管各的（ADR-0009）

1. **leaf 契约层** — `tests/*.test.mjs`。跑 `cvsim/lab/static/*.js` 里的纯逻辑
   叶子（零 import、零 DOM），`node --test` 直跑，无浏览器、无构建。
   纯逻辑改动的**第一道防线**放这里。
2. **整页集成** — `tests/lab_*_probe.mjs`。真起 uvicorn + headless 浏览器 + CDP，
   验 DOM 装配和像素。慢，且依赖本机环境。
3. **源码形状守卫** — `tests/test_lab_ui.py`。断言"源码里有某串"这类结构性质。
   这类断言**不是行为测试**，文件里有一份 `SHAPE_GUARDS` 表逐条标注理由，
   并有 meta-guard `test_shape_guards_are_declared_not_silently_behavioural`
   防止有人悄悄把它当行为测试用。

`tests/test_frontend_leaf_suite.py` 是第 1 层的**数量守卫**：磁盘上的 leaf 测试
文件集合和 CI 命令一旦不一致就红（漏文件、或写了测试却没接进 CI）。

## 探针的环境变量（§4.4 新增）

探针原先硬编码 Windows Edge 路径和 `.venv/Scripts/uvicorn.exe`，在 ubuntu CI
上永远跑不了。现在统一走 `tests/probe_env.mjs`：

| 变量 | 作用 | 默认 |
| --- | --- | --- |
| `EDGE_PATH` | 浏览器可执行文件 | 按 `process.platform` 猜（Windows 两个常见安装位置 / macOS 的 Edge.app / Linux 走 PATH 的 `microsoft-edge`） |
| `UVICORN` | uvicorn 可执行文件 | `.venv/Scripts/uvicorn.exe`（Windows）或 `.venv/bin/uvicorn` |
| `PROBE_PORT` | lab server 端口 | 各探针自己的历史默认值（8765–8773 / 8860） |
| `PROBE_CDP_PORT` | CDP 调试端口 | 各探针自己的历史默认值（9223–9231） |

端口设了环境变量就能并行跑多个探针（原先两对是撞车的：8860+9224 和 8771+9229）。
探针 profile 目录写到系统临时目录，不再往仓库根写 `.probe-*`。

跑探针产生的临时目录用完请删（`AGENTS.md` 项目约定）。

## golden 与重生成

四套 golden，**重生成命令各不同，别记混**：

| 产物 | 位置 | 重生成 |
| --- | --- | --- |
| API golden（9 个 JSON） | `tests/golden/responses/` | `.venv/Scripts/python.exe tests/golden/capture_golden.py` |
| SF golden（npz） | `tests/_golden/sf_fock_golden.npz` | `.venv/Scripts/python.exe tools/gen_sf_golden.py`（需 StrawberryFields venv） |
| piquasso golden（npz） | `tests/_golden/piquasso_fock_composite_golden.npz` | `tools/gen_piquasso_golden.py`（需 piquasso venv） |
| 像素基线 | `tests/lab_heatmap_pixels.json` | `node tests/lab_heatmap_pixel_probe.mjs --write` |

**SF golden 与 piquasso golden 分工不重叠**，别以为多此一举：

- SF golden：1–2 模**门演化**，8 例，无 3+ 模、无测量、无条件化、无通道
- piquasso golden：**3/4 模非高斯链 + PNR 联合分布 + PNR 后选择条件化**——正是 SF 盖不到、而 cvsim 又没有闭式的那几格

生成脚本有一处**故意不同**：`tools/gen_sf_golden.py` 会先算
`max|SF−cvsim| < 1e-8`，不过就 `sys.exit` 不写盘；`tools/gen_piquasso_golden.py`
**不对 cvsim 自检**——参考实现输出原样落盘，cvsim 对比只打印不设门。
自检版只能**锁住**已有的一致性、**发现不了**分歧；分歧必须表现为红的测试。

两者都**不 import piquasso/SF 于测试期**，CI 也不装它们（`tools/qualify_piquasso_oracle.py`
是先做资格认证用的：43 条 cvsim 闭式判据，全过才敢把它当 oracle）。

`capture_golden.py` 的 docstring 曾声称 `--check`，但**代码里没有 argv 处理**，
那个选项从来不存在（检查逻辑实际在 `test_lab_golden.py` 里）—— 审计 §4.9 已记录。

## marker 是选择器，不是执行门

`pyproject.toml` 里声明了 `phaseB1`–`phaseB10` 十个 marker，用 `-m phaseB9` 之类
可以只跑某一批。**CI 里没有任何 `-m phaseB*` 任务** —— 全套测试每次都跑。
marker 只用于本地聚焦，别把它当成覆盖率/执行门。

> 审计 §4.8 修正过两处：`test_b7_kernel_log_domain.py` 原先误标 `phaseB6`
> （已改 `phaseB7`）；`test_b9_bosonic_pnr.py` / `test_b10_bosonic_pnr_joint.py`
> 的文件存在但**没打 marker**（已补，否则 `-m phaseB9` 选不到）。

## 环境一致性警告

`.venv` 必须是 **Python 3.13 + numpy 2.5.1**（见 `uv.lock`，numpy 按 Python
版本分叉）。裸 `uv`（默认 3.10/numpy 2.2.6）会让 golden 类测试失败。

12 个 skip 是 thewalrus 造成的（numba 要求 numpy ≤ 2.4，项目 pin 2.5.1），
不是失败。
