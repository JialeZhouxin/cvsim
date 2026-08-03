# Implement — Gaussian Lab L0

> 上游: `design.md`。每步验证后才进下一步。

## 步骤

### S1: 依赖 + 包骨架
- `pyproject.toml`: `[project.optional-dependencies] lab = ["fastapi>=0.110", "uvicorn>=0.27"]`；`dev` 加 `httpx`
- `uv sync --extra lab --extra dev`（或等价）→ verify: `uv run pytest tests/ -q` 现有 379 全绿
- 建 `cvsim/lab/__init__.py` + `ir.py` + `server.py` 空骨架
- verify: `uv run python -c "import cvsim.lab"`

### S2: F-LAB-IR — schema + 引擎
- `ir.py`: `CircuitV0Error`、`Node/CircuitV0/View` dataclass、`load_circuit` 校验、`run_circuit`
- `tests/test_lab_ir.py`: 验证表 + golden 等价 + heterodyne 删模 + homodyne 不删模 + view 重映射
- verify: `uv run pytest tests/test_lab_ir.py -q` 绿

### S3: F-LAB-API + F-LAB-WIGNER — FastAPI
- `server.py`: `app`、`GET /health`、`POST /run`（422 带原因）
- `tests/test_lab_api.py`: /health、/run 主剧本、422、A4 vacuum Wigner、A8 private-import 守卫
- verify: `uv run pytest tests/test_lab_api.py -q` 绿

### S4: 收尾
- `uv run pytest -q` 全套（379 + 新增 ≈ 400+）
- `uv run ruff check cvsim/lab tests/test_lab_ir.py tests/test_lab_api.py`
- vision-gaussian-lab-ui.md changelog 加 L0 条目（注明 L0 落地，L1 起拖拽）
- `task.py finish` + 视结果 archive

## 验证命令清单

```bash
uv sync --extra lab --extra dev
uv run pytest tests/test_lab_ir.py -q
uv run pytest tests/test_lab_api.py -q
uv run pytest -q
uv run ruff check cvsim/lab tests/test_lab_ir.py tests/test_lab_api.py
```

## 不做清单（再次确认）

- ❌ 前端 / 拖拽 / 任何 HTML（L2）
- ❌ `/sample`、seed 抽样、Measure once（L3）
- ❌ Save/Load 文件端点（L3）
- ❌ 扫参、undo、非白名单 op、`ui` 子树参与编译
