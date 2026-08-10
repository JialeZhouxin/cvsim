# PRD — phase4-ad-objective-notebook

## Goal
可微目标 + 优化 notebook：`cvsim/gaussian/ad.py`（apply + 可微 log_neg）+ `tutorials/05_ad_designer.ipynb`。

## Deliverables
- `cvsim/gaussian/ad.py`: `apply_gaussian` / `log_neg_loss`（jnp 镜像 analyse.log_negativity，公式互链）/ 优化辅助
- `tests/test_ad_objective.py`: log_neg 梯度 vs FD（r、θ）；优化收敛到解析最优 r*(η)
- `tutorials/05_ad_designer.ipynb`: TMSV → 损耗 η → 最大化 E_N；教学：纠缠生存曲线 + 反向设计

## Acceptance
- exit 1 收口：梯度 vs FD 全参数通过
- exit 2 收口：numpy/jax 共享测试（参数化）
- notebook Run-All 通过；优化终点与解析值一致（标注 η 阈值处纠缠死亡）
