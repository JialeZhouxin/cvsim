## 概述

三表示核心包(gaussian/fock/bosonic)各公开一个 `ir_schema()` 只读数据快照函数,作为 schema 知识的权威入口。这是 [Lab schema 单一事实源 spec](见 spec.md) 的票 1/4。

**设计共识**(grilling 2026-09-03,详见 spec):核心表示包是 schema 权威 → Lab 组装 → `GET /schema` 下发。本票只做核心侧,Lab 零改动。

## 变更

1. `cvsim/gaussian/ir.py` / `cvsim/fock/ir.py` / `cvsim/bosonic/ir.py` 各新增:

   ```python
   def ir_schema() -> dict[str, Any]:
       """只读 schema 快照:op 形状(arity/value_kind/defaults)+ initial 注册表。"""
   ```

   纯数据 dict,不含 `OpMeta` 类实例(类保持私有)。
2. bosonic:`circuit.py` initial elif 链改数据驱动(名字→工厂映射表,数据从注册表来);fock `_validate_initial` 对齐同一注册表模式。
3. 三包 `__init__.py` `__all__` 各 +1(`ir_schema`);`tests/test_public_api.py` 快照同步(新增导出 = MINOR,政策允许)。
4. 每包 `ir_schema()` 形状 golden 单测(冻结键集与类型)。

## 验收

- [ ] pytest 全绿(含 test_public_api 快照)
- [ ] 三包 `ir_schema()` golden 测试过
- [ ] bosonic/fock 的 initial 校验行为不变(现有 `test_gkp_2d_frontend_initial` 等全过)
- [ ] Lab 代码零改动(票 2 才消费)

**Blocks**: schema 组装票(下一步)
