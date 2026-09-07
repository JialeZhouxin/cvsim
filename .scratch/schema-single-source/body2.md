## 概述

Lab 层新增 schema 组装模块 + `GET /schema` 端点 + pytest 数据级交叉断言(双写期防线,进 CI)。票 1(核心 `ir_schema()`)完成后执行。

## 变更

1. **`cvsim/lab/schema.py` 新模块(Lab schema 组装)**:调三包 `ir_schema()`,叠三份白名单解锁子集,声明 Lab 扩展字段边界(initial 形状/cutoff/view/seed),输出 `/schema` 载荷(形状见 spec)。
2. **`server.py` 加 `GET /schema`**(轻,与 /health 同级,纯静态序列化)。
3. **报错数据单点化**:白名单/initial 类 `CircuitV0Error` 携带 `{code, op, allowed}` 结构;`server.py` HTTPException 层统一拼文本。现有 422 文本语义不变,格式归并(三份白名单消息格式不一 → 一致)。
4. **pytest 数据级交叉断言**(CI 防线):TestClient 拉 `/schema` ↔ 正则抽取 ops.js `backends` 字段 + initial 名单,数据级比对。双写期两套并存,此断言防漂移。

## 验收

- [ ] pytest 全绿
- [ ] `/schema` golden 测试(载荷形状冻结)
- [ ] 交叉断言测试过且在 CI 跑(tests/ 下,pytest)
- [ ] 旧代码行为不变:ops.js/ir.py 原样,仅新增
- [ ] 报错文本语义不变(golden 422 消息测试)

**Blocks**: 前端消费端切换(票 3)、后端切换+删镜像(票 4)
