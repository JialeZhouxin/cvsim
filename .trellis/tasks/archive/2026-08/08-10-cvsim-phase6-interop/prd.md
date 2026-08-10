# Phase 6 C1 — Interop ordering（vision §8）

## Goal

`cvsim/interop/ordering.py`：quadrature ordering 转换（xxpp ↔ xpxp），
补全 vision §8 interop 表第一行。纯排列、零表示依赖、不引入新依赖。

## 决策（grill 2026-08-10 四问全锁定）

| Q | 决策 |
|---|------|
| Q1 模块位置 | `cvsim/interop/ordering.py`（vision §2.1/§8 原样）；walrus 已定型不搬 |
| Q2 范围 | 最小函数级：`to_xpxp(V, rbar)` / `from_xpxp(V, rbar)`，ndarray in/out；不加 GaussianState 方法、不做 Fock dm |
| Q3 hbar | 纯排列不带 hbar 参数；docstring 注明 ħ=1 元数据；SF(ħ=2) 缩放是调用方责任 |
| Q4 SF 测试 | golden 自证（round-trip identity + 手算解析值硬编码）+ `docs/sf-roundtrip.md` 对照脚本；本机无 SF 不写 skipif 死代码；pyproject 预留 `[sf]` extra（可选） |

## Requirements

- `cvsim/interop/__init__.py` + `cvsim/interop/ordering.py`：
  - `to_xpxp(V, rbar)` → `(V_xpxp, rbar_xpxp)`：xxpp 排列 (x₁..x_m, p₁..p_m) → xpxp (x₁,p₁,...,x_m,p_m)
  - `from_xpxp(V, rbar)` → `(V_xxpp, rbar_xxpp)` 逆变换
  - 轻校验：2m 偶维、V 对称、rbar 长度匹配（ValueError）
- `tests/test_interop_ordering.py`：
  - round-trip：to_xpxp ∘ from_xpxp = identity（随机辛 V + rbar，种子固定）
  - golden：单模挤压真空 r → xpxp V = ½·diag(e^{-2r}, e^{2r})；2 模 TMSV 解析 V 的 xpxp 期望（手算硬编码）
  - 校验：奇维/不对称抛 ValueError
- `docs/sf-roundtrip.md`：SF(ħ=2) 对照脚本（V_sf = 2·V_ours 缩放 + 排列 + round-trip 验证代码）
- vision §10 gap table 加 Interop ordering 行 + §8 表头确认

## Acceptance Criteria

- [ ] AC1: 新函数 + 测试全绿；全量 pytest 758+（无回归）
- [ ] AC2: golden 值手算可复现（测试注释写推导）
- [ ] AC3: api-freeze 白名单更新（若公共导出）+ commit + OCR
- [ ] AC4: gap table / vision 同步

## 排除

- walrus 迁移、SF 运行时依赖、skipif 测试（无环境验证）、GaussianState 方法、hbar 参数
