# ADR-0003: circuit_v1 核心 IR（serialize 收编）

- 日期: 2026-08-07
- 状态: 已接受

## 背景

Lab UI 从 v0 起以 `circuit_v0` JSON（`cvsim/lab/ir.py`）探路 serialize（vision-gaussian-lab-ui §7）。
Phase 3 正式收编：核心需要一份正式电路 IR，`GaussianCircuit` 可序列化，Lab 变纯消费者。
grill（一次一问 + 推荐答案 + 权衡）收敛 8 项决策，用户逐项确认。

## 决策

1. **单一正式 IR `circuit_v1`**，放核心 `cvsim/gaussian/ir.py`；Lab 不再自持格式，
   迁移为消费者（v0 旧文件经纯函数翻译，golden 等价测试兜底）。
2. **无源概念**：顶层 `nmode`，所有源是门/通道的精确特例——coherent≡displace、
   tmsv≡two_mode_squeeze、thermal≡amplifier(G=1+2nbar)。执行 = 建真空 → 顺序应用 ops。
   砍掉 source 节点类别、source-first 校验、多源 product 逻辑。
3. **全 op 集 1:1** 对齐 `GaussianCircuit` builder（14 op），`to_ir()/from_ir()` 往返无损；
   Lab 白名单仍是 UI 概念，留在 Lab 层执行。
4. **参数编码**：扁平命名 `params` dict；值枚举 = number / 复数 `[re,im]` / 矩阵嵌套数组 /
   `{"$param": name}` 符号参数 / `{"$ref": name, "gain": g}` 前馈；省略参数 = 库默认值。
5. **统一 `modes` 数组**（不分 mode/modes）；数组序 = 执行序；测量删模后逻辑索引重映射（运行时）。
6. **校验分工**：IR 层结构校验（类型/字段/arity），物理范围校验留库函数（复用 Lab 现模式）。
7. **版本化**：破坏性变更走 `circuit_v2`，不静默改语义（vision §7.6）。
8. **Lab 直接迁 v1**：`load` 接受 v0（翻译）+ v1；`save` 写 v1；`view/seed/ui` 为顶层
   扩展字段（核心忽略，vision §7.5 允许），其余未知顶层字段拒绝。
9. **`id` 可选**：省略按数组序生成 `n0,n1,…`；存在则校验唯一性；核心逻辑不依赖 id。

## 权衡

- 曾考虑「信封方案」（v0 外壳内嵌 v1）：被否。vision §7.5 已允许 ui 子树被后端忽略，
  直接 v1 + 扩展字段更扁平，无嵌套。
- 曾考虑保留 source 节点类别：被否。源=门的等价是精确数学事实（非近似），
  砍掉整类节点 + 特例规则换来 IR 只含一类 op。
- 曾考虑位置数组参数（省字节）：被否。命名 dict 自描述、顺序无关、省一张 op 参数映射表；
  单用户本地 JSON 体积无意义。
- 曾考虑必填 id：被否。核心是纯物理，id 是 Lab 引用句柄，可选即可。
- 曾考虑双 schema 并存：被否。收编即单点真理，两个 schema 永不共存。

## 后果

- `cvsim/gaussian/ir.py` 新建；`lab/ir.py` 拆为 v1 引擎 + v0 翻译层（ADR-0001 #5 触发器已触发）。
- Lab 保存的 JSON 从 v0 变 v1；旧文件自动翻译，用户无感。
- `GaussianCircuit` 增加 `to_ir()/from_ir()` 公开 API（并入 F-CIRCUIT-PROD 序列化项）。
- 术语更新进根 CONTEXT.md（circuit_v1、统一 modes、翻译层）；vision §10 gap 表同步。
