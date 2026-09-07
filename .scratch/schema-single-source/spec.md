# Spec: Lab schema 单一事实源（schema snapshot + assembly + endpoint）

> 来源:`/improve-codebase-architecture` 审查(2026-09-03)+ `/grill-with-docs` 12 问拷问(2026-09-03)。
> 术语见根 `CONTEXT.md`:**表示包 schema 快照 (schema snapshot)**、**Lab schema 组装 (schema assembly)**、**初始态字段 (initial)**、**circuit_v1**。
> 分层决策与架构词汇(module / interface / depth / seam / adapter / leverage / locality)按 codebase-design。

## 问题(审查确认的事实)

同一份 circuit_v1 schema 的"合法形状"知识散在 7 处,手写镜像:

1. ops.js 每 op 的 `backends` 字段 + `FOCK_PALETTE`/`GAUSSIAN_PALETTE` 手写列表
2. editor.js `stateFromJson`/`stateFromV1`(view/seed/backend 校验逐字重复两遍)
3. ir.py `LAB_WHITELIST`/`FOCK_WHITELIST`/`BOSONIC_WHITELIST` 三份
4. scan.py `SWEEPABLE_PARAMS`
5. initial.js `BOSONIC_SOURCES` + ir.py `_load_bosonic` 硬编码名单 + `cvsim/bosonic/circuit.py` elif 链
6. ops.js 3 张改名表 + editor.js 3 张反向表 + ir.py 2 张(`UI_TO_V1_OP`/`V0_TO_V1_OP`/`UI_TO_V1_PARAM`/`V0_TO_V1_PARAM`/`FOCK_UI_TO_V1_PARAM`/`FOCK_V1_TO_UI_PARAM`)
7. 报错文本内嵌 `sorted(WHITELIST)`,三份白名单消息格式不一

**事故背书**:gkp0_2d 新增时(`e907db9`)漏改 ir.py,422 往返(`cc0e297` 补救,间隔 5 小时)。

**方向性约束(用户锁定)**:后端(模拟器)未来可独立通过 API 调用,不与 Lab 前端绑死;schema 知识从后端流向任何消费者;前端可对接不同后端。因此 schema 权威必须在核心,不能在 Lab。

## 已锁定的设计决策(12 问)

| Q | 决策 |
|---|------|
| Q1 | 后端下发 + 运行时拉取;不做生成物、不做纯契约测试方案 |
| Q2 | schema 携带:op↔backend 成员、参数形状(名/类型/required)、可扫性、initial 名单、改名表、view 边界。UI 留 ops.js:label/tip/palette 分组/advanced/默认 sweep 范围/**参数 min-max 刻度** |
| Q3 | IR 名为正名(`measure_homodyne`),UI 名是每 op 一个 `uiName` 别名;6 张改名表消灭 |
| Q4+C | initial 源注册表在**核心**表示包(bosonic/fock 各自),Lab 引用;核心 elif 链改数据驱动 |
| Q5′+B | **分层权威**:核心表示包是 schema 权威 → Lab 组装(叠白名单子集 + 扩展字段声明)→ `/schema` 下发。白名单仍是 UI 概念留在 Lab(ADR-0003 #3 不变) |
| Q6+B | 范围(min/max)是 UI 教学刻度,不进 schema;schema 只携带核心真正拥有的约束(loss T∈[0,1] 是目前唯一核心级范围) |
| Q7+A | 前端启动一次 `GET /schema`,失败显式红条(不静默降级);无版本协商(同包同进程) |
| Q8+A | 报错数据从单点生成:结构化 `{code, op, allowed}`,Lab HTTPException 层统一拼文本;前端暂不消费 code |
| Q9+B | 三步迁移:①单点+端点+pytest 数据级交叉断言 → ②切消费端 → ③删旧镜像。交叉断言写 pytest(进 CI;CI 目前不跑 node --test/probe) |
| Q10+A | 三包各公开 `ir_schema()` 只读数据快照(进 `__all__`,公开面 MINOR);`OpMeta` 类保持私有 |
| Q11+A | Lab 扩展字段(initial/cutoff/view/seed/ui)边界由 Lab 组装层声明,核心保持 opaque(ADR-0003 #8 无冲突,不 amend) |
| Q12 | 术语已入 CONTEXT.md:`表示包 schema 快照`、`Lab schema 组装` |

## `/schema` 载荷形状(设计冻结)

```jsonc
{
  "backends": ["gaussian", "fock", "bosonic"],
  "ops": {
    "<IR名>": {
      "uiName": "homodyne | null(同名省略)",
      "backends": ["gaussian", "fock", "bosonic"],  // 白名单交集后的解锁子集
      "meta": { "arity": "one|two|all|any|none", "value_kind": {...}, "defaults": {...} },
      "core_ranges": { "T": [0, 1] }  // 仅核心真正强制的范围;无则省略
    }
  },
  "initial": {
    "fock":   { "kind": "int", "min": 0 },
    "bosonic": { "kind": "enum", "sources": ["gkp0", "gkp1", "gkp0_2d", "gkp1_2d"], "vacuum": null },
    "gaussian": null
  },
  "extensions": {
    "cutoff": { "min": 1, "max": 30 },   // fock-only,per-mode
    "view":   { "lim": [0.001, 50], "n": [2, 512] },
    "sweepable": { "squeeze": ["r"], "loss": ["T"], "...": "..." }
  }
}
```

注意:`ops` 以 IR 名为主键;`uiName` 反向取代 `UI_TO_V1_OP` 等全部 6 张表;`value_kind` 的语义按核心现有 OpMeta(`num|complex|matrix|str`)。

## 票拆分(tracer-bullet,每张独立可合并)

### 票 1:核心三包 `ir_schema()` 公开
- `cvsim/gaussian/ir.py`、`cvsim/fock/ir.py`、`cvsim/bosonic/ir.py` 各新增 `ir_schema()` → 纯数据 dict(op 形状 + initial 注册表)
- 三包 `__init__.py` `__all__` 各 +1 导出;`tests/test_public_api.py` 快照同步(新增导出 = MINOR,政策允许)
- bosonic initial 注册表把 `circuit.py` elif 链改数据驱动(工厂映射表);fock 同理对齐 `_validate_initial`
- 验收:pytest 全绿 + `test_public_api` 快照测试过 + 每包 `ir_schema()` 有单测(形状冻结 golden)

### 票 2:Lab schema 组装 + `GET /schema` + 交叉断言
- `cvsim/lab/schema.py` 新模块:调三包 `ir_schema()`,叠 `LAB_WHITELIST`/`FOCK_WHITELIST`/`BOSONIC_WHITELIST` 解锁子集,声明 Lab 扩展字段边界,拼 `/schema` 载荷
- `server.py` 加 `GET /schema` 端点(轻,与 /health 同级)
- **报错数据单点化**:白名单/initial 类 `CircuitV0Error` 改为携带 `{code, op, allowed}` 结构,`server.py` 拼文本(现有 422 文本语义不变,格式统一)
- **pytest 数据级交叉断言**(进 CI):TestClient 拉 `/schema` ↔ 正则抽取 ops.js 的 `backends` 字段/initial 名单,比对一致(双写期防线)
- 验收:pytest 全绿;`/schema` golden 测试;交叉断言过

### 票 3:前端消费端切换
- app.js `init()` 拉 `/schema`,失败显式红条;ops.js 运行时合并(backends/参数形状/required/uiName 来自 schema,label/tip/刻度/palette 留守)
- editor.js `stateFromJson`/`stateFromV1` 的 view/seed/backend 校验改查 schema(消灭两份逐字重复)
- `toV1Json`/`stateFromV1` 改名逻辑改查 `uiName`(6 张表删除)
- initial.js 名单/选项表从 schema 合并;`remapForBackend` 逻辑保持纯函数但名单数据来自 schema
- node --test(editor.test.mjs)适配:合并逻辑注入 mock schema(纯函数化,zero-dep 测试保留)
- 验收:node --test 全过 + 手跑 probe(lab_staff/lab_bosonic/lab_undo/lab_scan)+ test_lab_ui.py 过

### 票 4:后端消费端切换 + 删旧镜像
- ir.py 三份白名单改为从 Lab schema 组装层派生(常量变派生视图);scan.py `SWEEPABLE_PARAMS` 从 schema 派生
- 报错文本模板全部走单点(38 处 raise 逐类归并:whitelist/initial/view/seed)
- 删旧镜像:ops.js `backends` 字段、`FOCK_PALETTE`/`GAUSSIAN_PALETTE` 手写表、initial.js `BOSONIC_SOURCES` 常量
- **删除票 2 的交叉断言**(双写结束,镜像已不存在)
- 完成标志:`grep backends cvsim/lab/static/ops.js` 只剩注释;`grep BOSONIC_SOURCES cvsim/lab/static/initial.js` 为空
- 验收:pytest + node --test 全过;手工主剧本(vision §5)走通三后端

## 依赖边

- 票 2 blocked by 票 1
- 票 3 blocked by 票 2(前端要拉端点)
- 票 4 blocked by 票 2、3(消费端全切后才能删镜像)
- 票 3 与票 4 的"ir.py 报错单点化"部分无相互依赖,可并行

## 非目标(YAGNI,本次不做)

- 参数 ranges 全面进核心(Q6:只有 T 已有;未来 API 收严时增量加)
- 版本协商 / schema_rev(Q7)
- 前端机器可读 code 分流(Q8 留扩展)
- 多后端插拔 adapter seam(Q5′ C 否决:one adapter = hypothetical seam)
- v0 翻译层的改名表(它消费的是历史 UI 名,保留在 ir.py `translate_v0` 原样)
- machine-readable code 前端消费(留扩展空间)

## 验收总口径

- 加一个新 op(含新 initial 源) = 改**核心一个文件**(ir.py OP_META + 工厂/注册表)+ UI 元数据一行(label/tip/刻度);**不再改 ir.py 白名单/initial.js/ops.js backends/editor.js 校验**
- gkp0_2d 式事故(核心加了、入口漏)在结构上不可能复发:Lab 白名单与 initial 名单是派生物
- CI(pytest)覆盖 schema 一致性;node --test 覆盖前端合并逻辑
- vision-gaussian-lab-ui.md §6.2 的 import 禁令不放松(Lab 仍只用三包公开面)