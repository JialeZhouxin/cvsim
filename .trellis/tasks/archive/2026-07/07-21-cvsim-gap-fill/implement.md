# Implement · gap-fill 包 A（父）

## Preconditions

- [ ] 用户批准本规划
- [ ] **勿**在父任务直接堆 G1–G4 代码；先 `task.py create` 子任务

## Sequence

```text
1. 批准后：创建子任务 G1、G2、G3、G4（G4 prd 写 depends G1–G3）
2. task.py start G1 → 实现 → archive
3. task.py start G2 → 实现 → archive   # 可与 G1 并行会话，本会话串行
4. task.py start G3 → 实现 → archive
5. task.py start G4 → UAT/docs → archive
6. 父任务 AC 勾选 → archive 父
```

## Child create templates

```bash
py -3 ./.trellis/scripts/task.py create "Fock 单模 Wigner" --slug cvsim-fock-wigner --description "G1: single-mode Fock/ρ Wigner; vac 1/π; |1> center neg"
py -3 ./.trellis/scripts/task.py create "FockDensity 门 D/R/S" --slug cvsim-fock-density-gates --description "G2: UρU† for D/R/S on FockDensity; after loss"
py -3 ./.trellis/scripts/task.py create "sample_and_condition 薄封装" --slug cvsim-sample-and-condition --description "G3: thin G/B sample+condition wrapper or demo"
py -3 ./.trellis/scripts/task.py create "P0 UAT 收口" --slug cvsim-uat-p0-close --description "G4: UAT U9 + docs; depends G1 G2 G3"
```

## Validation（战役末）

```bash
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
```

## Parent checklist

1. [x] 用户批准
2. [x] 四子任务创建
3. [x] G1–G4 全 archive
4. [x] 父 prd AC 全勾
5. [x] archive 父
