# 三表示拆耦合

## Goal

库内依赖：`B ↛ G` 运行时硬依赖；三包可独立理解。  
**无物理变更**；pytest/UAT 绿。

## Background

审计结论：

| 耦合 | 处理 |
|------|------|
| B gates → `gaussian.symplectic` | **A：S 上提到共享** |
| `from_gaussian(GaussianState)` | **C：duck type** |
| `wigner.py` 三态门面 | **保留**（故意跨表示 API） |
| demos/tests 跨表示 | 保留（验收层） |
| Fock | **零改** |

## Decisions

| # | 选择 |
|---|------|
| D0 | 方案 **A + C only**；不复制 S 进 B |
| D1 | 新路径：`cvsim/symplectic.py`（原 `gaussian/symplectic.py` 内容） |
| D2 | `cvsim/gaussian/symplectic.py` → **thin re-export shim**（兼容旧 import） |
| D3 | G/B `gates` 直接 `from cvsim.symplectic import …` |
| D4 | `from_gaussian`：协议式 `(V, rbar)`，去掉对 `GaussianState` 的 TYPE_CHECKING import |
| D5 | 不拆 `wigner.py`；不拆 `conventions` |
| D6 | 无新物理；无 API 语义变 |

## Requirements

### R1 共享 symplectic

- 模块：`cvsim/symplectic.py`
- 内容 = 现 `gaussian/symplectic.py`
- `gaussian.gates`、`bosonic.gates` 从共享 import
- 旧路径 `cvsim.gaussian.symplectic` 仍可用（re-export）

### R2 duck from_gaussian

```python
@classmethod
def from_gaussian(cls, state) -> BosonicState:
    """Wrap object with .V and .rbar as one component w=1."""
```

- 去掉 `from cvsim.gaussian.state import GaussianState`
- 现有 `BosonicState.from_gaussian(GaussianState(...))` 仍跑

### R3 验收

- [ ] `rg "from cvsim.gaussian" cvsim/bosonic` → 无匹配（除注释）
- [ ] pytest 全绿；UAT 8/8
- [ ] README 包结构一句：S 共享、B 不依赖 G 包逻辑

## Acceptance Criteria

- [x] **AC1** B 源码不 import `cvsim.gaussian.*`
- [x] **AC2** `from_gaussian` 可用 duck 对象
- [x] **AC3** 旧 `from cvsim.gaussian.symplectic import S_squeeze` 仍可用
- [x] **AC4** pytest **104** + UAT 8/8
- [x] **AC5** 文档结构更新

## Out of Scope

- 拆 wigner 三入口
- 复制 S 到 B
- Fock 改动
- 物理 / 新功能
- 拆成三个独立 pip 包

## Notes

- 目标：教学上「三个模拟器 + 共享辛矩阵地基」，不是 monorepo 拆 repo
