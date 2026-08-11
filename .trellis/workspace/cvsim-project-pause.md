# CV 高斯模拟器告一段落（2026-08-10 用户拍板）

项目状态快照：**Phases 0–5 全完成 + Phase 6 interop 落地一行，0 活跃任务，766 绿。**

## 完成度

| 里程碑 | 状态 |
|--------|------|
| Phase 0–1 Gaussian 核心（工厂/辛/门/干涉仪/通道） | ✅ |
| Phase 2 Analyse + 测量 + 教学（熵/纠缠/Heterodyne/API 冻结） | ✅ |
| Phase 3 Compile + 规模 + 采样（IR/编译/批量/GBS adapter/benchmark） | ✅ |
| Phase 4 可微设计（backend= 双后端 + ad.py + 优化教程） | ✅ |
| Phase 5 桥 + 纠错故事（F-BRIDGE/threshold/GKP 教程/Bosonic 一致性） | ✅ |
| Phase 6 interop（ordering xxpp↔xpxp） | ✅（B/C/D 方向未开） |
| vision §11 open questions | 5/5 Resolved |

测试面：**766 passed / 6 skipped / 1 warning**（基线 700 → 766，跨 4 天）。

## 真正遗留（诚实清单，非假装全完成）

1. **仓库无 git remote** → `.github/workflows/ci.yml` 5 job 从未实跑（仓库级现状，Phase 3 benchmark-ci 时实证）
2. `benchmarks/latest.json` 未提交（Phase 3 产物，每收口排除）
3. Fock/Bosonic 仍是 teaching MVP（bridge 已补观测值层；纠缠量跨表示截断收敛 = ponytail 注释）
4. Lab vision L5+ 未做（undo 等；L0–L4 已落地 + 14 项 polish）
5. SF 真对照测试未写（skipif 无环境验证 → docs/sf-roundtrip.md 脚本替代）
6. mypy 104 errors 全在 cvsim/（pre-existing 类型债，从未清零）
7. vision §2.1 规划 `interop/walrus.py` 实际落 `gaussian/walrus.py`（已文档化，不搬）

## 恢复点（想继续时从哪接）

- 方向 B：§7 数值预算（project_physical P2、m=1000 验证）
- 方向 C：§9 testing doctrine（@pytest.mark.phase 切片）
- 方向 D：Lab L5+（undo / F-LAB-SHOT 增强）
- SF skipif 测试：装 strawberryfields 后按 docs/sf-roundtrip.md 补

## 提交链（Phase 6 尾部）

`d1d7365`（interop feat）→ `798a907`（vision gap）→ `3fa87f0`（archive）→ `4322d98`（journal）
