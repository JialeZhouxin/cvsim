## 概述

后端消费端切到组装层派生 + 删除全部旧镜像 + 拆除双写防线。票 2、3 完成后执行。

## 变更

1. **ir.py 三份白名单**(`LAB_WHITELIST`/`FOCK_WHITELIST`/`BOSONIC_WHITELIST`)改为从 `lab/schema.py` 派生的视图(常量声明移进组装层)。
2. **scan.py `SWEEPABLE_PARAMS`** 从 schema 派生。
3. **报错文本模板全部单点化**:38 处 `CircuitV0Error` 按类归并(whitelist/initial/view/seed),文本由 `{code, op, allowed}` 数据统一拼。
4. **删旧镜像**:
   - ops.js `backends` 字段、`FOCK_PALETTE`/`GAUSSIAN_PALETTE` 手写表
   - initial.js `BOSONIC_SOURCES` 常量 + ir.py `_load_bosonic` 硬编码名单(改查组装层)
5. **删除票 2 的交叉断言**(镜像已不存在,断言无对象)。

## 完成标志

```
grep backends cvsim/lab/static/ops.js   → 只剩注释
grep BOSONIC_SOURCES cvsim/lab/static/initial.js → 空
```

## 验收

- [ ] pytest + node --test 全绿
- [ ] 手工主剧本(vision §5)三后端走通
- [ ] gkp0_2d 回归演练:模拟"只加核心不加 Lab"→ 交叉断言时代 CI 红(票 2 后),删镜像后该操作变为"不可能遗漏"(白名单派生自动包含)
- [ ] `test_lab_ui.py` 的字符串 grep 契约升级或退役(数据级契约已在票 2)

**Blocks**: 无(终点)

## 总验收(spec 口径)

- 加一个新 op = 改核心 ir.py OP_META + 注册表(一个文件)+ UI 元数据一行;不再改 ir.py 白名单/initial.js/ops.js backends/editor.js 校验
