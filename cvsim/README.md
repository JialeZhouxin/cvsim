# cvsim · 三表示最小模拟器

从 `cv-photonic-notes` 理论笔记落地的 **Gaussian / Fock / Bosonic** MVP。  
依赖：`numpy` + `scipy`。约定：`ħ=1`，正交序 **xxpp**，真空 `V=I/2`。

## 环境

```bash
uv venv
# Windows
.venv\Scripts\activate
uv pip install numpy scipy
```

## 验收自检（README 最小闭环）

```bash
python -m cvsim.demos.m1_gaussian_squeeze   # 真空→挤压→V, det V, ⟨n⟩=sinh²r
python -m cvsim.demos.m2_fock_cutoff_scan   # 同电路扫 cutoff 逼近解析
python -m cvsim.demos.m3_cat_weights        # 小 cat 四组件 + ∑w=1
```

## 测试

```bash
uv pip install pytest
python -m pytest tests -q
```

## 包结构

```text
cvsim/
  conventions.py   # ħ, xxpp, Ω, vacuum
  gaussian/        # (V, r̄) + squeeze + det/⟨n⟩
  fock/            # 截断振幅 + squeeze(expm) + ⟨n⟩/norm
  bosonic/         # 组件列表 + even/odd cat
  demos/           # 里程碑自检
```

理论笔记（根目录 `*.md`）保持纯物理，不绑本包 API。
