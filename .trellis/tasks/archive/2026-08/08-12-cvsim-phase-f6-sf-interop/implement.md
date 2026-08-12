# Implement — Phase F6: SF interop + density export

## 顺序检查清单

### Commit 1 — golden 生成 + 对照套件（design.md 已含全部实证拍板：BS 映射 / 分层 cutoff / dm 全存）
- [ ] `tools/gen_sf_golden.py`（每个 prog 新建 Engine；simps shim；版本/日期记录；metadata JSON）
- [ ] 运行生成 → `tests/_golden/sf_fock_golden.npz`（8 组 dm：squeezed@50 / displaced@12 / rotated@10 / kerr@10 / bs_11@10（SF 原值 BSgate(π/4,0.2)）/ s2_00@30 / chain@45 / thermal_dm@10 + metadata）
- [ ] `tests/test_sf_golden_f6.py`（npz 对照，无 SF import；复数 dm 逐位 atol 1e-9；bs_11 侧用 `beamsplitter(−π/4, −0.2)`；全部经 `FockDensity.from_pure` → rho 比对）
- → verify: `py -3 -m pytest tests/test_sf_golden_f6.py -q` 全过；生成脚本可重跑（idempotent）

### Commit 2 — 文档
- [ ] `docs/sf-roundtrip-fock.md`（约定表含 **BS 映射 cvsim(θ,φ)=SF(−θ,−φ)** / ħ 无关性 / 双向 copy-paste / 密度导出格式 / 陷阱含 Engine 复用残留 + ket()=None / 重新生成）
- [ ] `docs/vision-fock-simulator.md`：F6 done 状态 + gap 表 + 文档控制 v0.5.0
- → verify: 文档脚本段可用 SF venv 实跑（doc 内脚本逐段测试）

### 收尾
- [ ] 全套件回归：`py -3 -m pytest tests/ -q`（959 + 新增，绿）
- [ ] OCR review 任务 commit（强制）
- [ ] commit 顺序：`test(fock): F6 SF golden 对照套件` → `docs: F6 SF round-trip 文档 + vision 同步`
- [ ] `task.py finish` + `task.py archive`

## 验证命令

```bash
/tmp/sfenv/Scripts/python.exe tools/gen_sf_golden.py      # 生成 npz（SF venv）
py -3 -m pytest tests/test_sf_golden_f6.py -q             # 对照套件
py -3 -m pytest tests/ -q                                 # 全套件回归
```

## 风险文件 / 回滚点

- SF 版本漂移：npz 内 metadata 版本锁；测试只读 npz
- 相位符号风险：生成脚本内先概率粗对齐再全复数；golden 与 cvsim 同源公式（thewalrus）非自证 — 独立实现路径（SF 引擎全链路 vs cvsim 直接 expm/闭式）
- 纯新增，单 commit 可回退

## follow-up（start 前）

- [ ] PRD/design/implement 三件齐 + 用户已批准
- [ ] implement.jsonl / check.jsonl 已放真实 spec 条目
