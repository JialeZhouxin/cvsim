# ADR-0008: Lab 统一结果规约（LabResult）

## 状态

Accepted（2026-09-04，/grill-with-docs 拷问后定案）

## 背景

Lab 三后端（gaussian/fock/bosonic）的响应组装是**双规约**：gaussian 经 `RunResult` dataclass → `server._payload` 转 dict，fock/bosonic 各自手造 payload dict。后果：wigner `{x,p,W}` 切片在 4 处重复；meter 键集三套无声明处；bosonic 跨包 import fock 私有 `_fock_measured`；gaussian payload 缺 `backend` 键，前端靠"键缺席"隐式分派。

## 决策

1. 新建 `cvsim/lab/result.py` 定义 **LabResult**：三后端统一的结果规约，字段**构造时即 JSON-ready**；`serialize()` 单点出 dict；`wigner_slice` / `measured_from_results` 收编为其私有函数。
2. **删除 `RunResult`**（含 `lab.__all__` 置换，仍 11 名）：留中间态 = 双规约换个房间继续住。
3. meter 键集**不拉齐**，以**meter 支持矩阵**声明（核心三键 + 表示扩展键），随 `/schema` 下发；差异是物理事实，永不 fabricated None。
4. gaussian 补 `backend: "gaussian"` 键——公共核心必填，响应自报家门。
5. 范围排除曲线形端点（/scan、/fidelity）与 /batch 直方图——单生产者、无镜像、形状不同，纳入只会搅浑契约。

## 理由（取舍）

- **完全统一 (a)** vs 半统一共享装配 (b) vs 扩展 RunResult (c)：(b) 留下三套调用约定继续漂移；(c) 把 RunResult 变成满是 None 的杂物袋（rbar/V 对 fock 无意义）。(a) 换来 server 零特判 + /sample 重复行收敛 + 序列化不可能错。
- **JSON-ready 构造**：把"序列化正确性"从约定变成构造不变量——一个存在的 LabResult 必然可序列化。
- **矩阵不拉齐**：全后端补齐键集会制造 None 假数据，违反本项目"永不 fabricated 数据"戒律；统一的价值在声明处单点，不在键集一致。
- **单票原子替换**：拆票只能拆出"加 LabResult 但不切换"的双轨半成品，正是 schema 票刚清除的双写反模式；golden 回归 + 结构守卫兜底原子性风险。

## 后果

- 加新后端 = 填一张 LabResult + 矩阵行，响应形状知识单点。
- 前端零改动兼容（键集只增不减，字节级差异 = gaussian 新增 backend 键）。
- `RunResult` 是公开面移除——但消费者已核实仅 lab 内部，且 `cvsim.lab` 不在 api-stability 的 semver 承诺内（只锁核心三包）。
- 前端按矩阵渲染 meter 行 = 后续独立小票，本决策不含。（2026-09 已关单：
  `schema_store.meterKeys` 唯一消费口 + `renderMetersPanel` 矩阵驱动渲染，
  gaussian 隐式键缺席分派与 bosonic 硬编码 "—" 退役；补 mean_photon_per_mode 行）