# 三表示 Jupyter 新手教程

## Goal

给 **光量子 / CV 新手** 写 **3 个可运行 Jupyter**，分别教 Gaussian / Fock / Bosonic。  
读完能：**会跑、懂数字、知道何时换表示、知道诚实边界。**

## Audience

- 会一点 Python / numpy  
- 听过量子态，未必会 CV 光学  
- **不** 假设 DeepQuantum / SF / 电路 DSL  

## Deliverables

| 文件 | 主题 |
|------|------|
| `tutorials/01_gaussian_beginner.ipynb` | 高斯：真空·门·Homodyne·loss |
| `tutorials/02_fock_beginner.ipynb` | Fock：截断·门·PNRD·loss→ρ·Wigner |
| `tutorials/03_bosonic_beginner.ipynb` | Bosonic：cat·GKP·权重·测量 |

配套（最小）：

- `tutorials/README.md`：怎么开环境、读序、三表示一句话  
- 根 / `cvsim` README **一行入口**（不写成长文）

## Pedagogy（每篇结构）

固定 6 段，短：

1. **这是啥 / 为啥用**（3–5 句直觉）  
2. **约定钉死**：ħ=1，xxpp，`V=I/2`  
3. **最小可跑闭环**（10–20 行代码）  
4. **数字检查**（与解析对照：`det V`、`sinh²r`、∑w 等）  
5. **再进一步**（1–2 个小实验：扫参 / 对照）  
6. **诚实边界 + 何时换表示**

风格：

- **中文**为主；关键英文术语后附中文  
- 每格少废话；先图/数，后一句物理解释  
- **禁止** 在理论 MD 风格里塞一整本 API  
- 可引用笔记章节标题（纯物理），不在教程里贴大段公式墙  

## Scope per notebook

### T1 Gaussian

- 真空 → `squeeze` → `det V`、`⟨n⟩=sinh²r`、`var x/p`  
- `displace` + Homodyne mean  
- 2 模：`squeeze` + `beamsplitter`  
- `loss(T)`；可选 `nbar` 一句  
- `homodyne_condition` / `sample` 各一小格  

### T2 Fock

- `fock` / vacuum；cutoff 不够会怎样（扫 N）  
- 1 模 D/S；2 模 BS 或 S₂ 之一  
- `pnrd_probs`  
- `loss → FockDensity`；1 模 Wigner（真空 1/π、|1⟩ 中心负）  
- Homodyne mean；condition **诚实：截断投影 ≠ G Kalman**  

### T3 Bosonic

- `even_cat`：4 组件、∑w=1、phase  
- `gkp0` 1d none / full；可选 2d 对角一眼  
- `gkp_logical_overlap` 教学一句  
- 门保持 w；`loss`；sample 或 condition 小演示  
- **何时用 B 而不是 G/F**  

## Out of scope

- 第 4 本「跨表示对照」长教程（已有 `m4` demo；README 链过去即可）  
- 新物理 API  
- HTML 美化 / 录屏  
- 改 `cvsim` 核心（教程只消费现 API）  
- 安装 jupyter 写进强制依赖（文档说明可选 `uv pip install jupyter matplotlib`）  

## Decisions

| # | 选择 |
|---|------|
| D0 | 目录 **`tutorials/`**（英文路径，Windows 友好） |
| D1 | 3 本独立 notebook + 1 README；不合成 1 本巨册 |
| D2 | 绘图：**matplotlib 可选**；没有也能跑核心 assert 格 |
| D3 | 每本末尾 **自检 cell**：`assert` 关键数字，失败即红 |
| D4 | 路径：notebook 内 `sys.path` 或假定从 repo 根起 kernel |
| D5 | 不引入新包依赖进 `pyproject`；教程 README 写可选依赖 |

## Acceptance Criteria

- [x] **AC1** 三本 notebook 从 repo 根可打开；关键 cell 可执行  
- [x] **AC2** 每本有自检 assert（vac / sinh²r / ∑w / W 等）  
- [x] **AC3** 每本有「诚实边界」段  
- [x] **AC4** `tutorials/README.md` 说明环境 + 阅读顺序  
- [x] **AC5** 不破坏现有 pytest **139** / UAT 8/8（教程不进强制 CI 亦可）  

## Success（用户视角）

兄弟能自己说：

1. 高斯态用 V 和均值描述，挤完 ⟨n⟩ 对不对  
2. Fock 截断是啥毛病、loss 为何变密度矩阵  
3. cat/GKP 为啥要多组件、∑w 为啥要 1  
