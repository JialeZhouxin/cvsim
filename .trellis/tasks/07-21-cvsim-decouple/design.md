# Design · 拆耦合 A+C

## Before

```text
bosonic/gates ──→ gaussian/symplectic
bosonic/state ──→ gaussian.state (TYPE_CHECKING + from_gaussian)
```

## After

```text
gaussian/gates ──→ cvsim/symplectic.py
bosonic/gates  ──→ cvsim/symplectic.py
gaussian/symplectic.py  = re-export shim only
bosonic/state.from_gaussian  = duck (.V, .rbar); no GaussianState import
```

## File ops

1. 读 `gaussian/symplectic.py` → 写 `cvsim/symplectic.py`（同内容，改模块 docstring）
2. `gaussian/symplectic.py` 改成：

```python
"""Compat re-export. Prefer cvsim.symplectic."""
from cvsim.symplectic import *  # noqa
from cvsim.symplectic import (
    S_beamsplitter,
    S_phase,
    S_squeeze,
    S_two_mode_squeeze,
    d_displace,
)
```

3. `gaussian/gates.py` / `bosonic/gates.py`：import 改 `cvsim.symplectic`
4. `bosonic/state.py`：删 TYPE_CHECKING；`from_gaussian` duck
5. README 包结构：`symplectic.py` 标共享

## Test add

`tests/test_decouple.py`（轻）：

- `from_gaussian` 对简单 namespace `(V, rbar)` 工作
- optional：assert `cvsim.bosonic.gates` 源码不 import gaussian（或跳过，用 rg 人工）

## Risk

| 风险 | 缓解 |
|------|------|
| 循环 import | symplectic 只 numpy；G/B 单向依赖它 |
| 旧测试 path | shim 保留 |
