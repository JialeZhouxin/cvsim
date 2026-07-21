# Implement · P1 包 A 父

## Preconditions

- [x] 用户批准
- [x] 创建子任务 G8、G7

## Sequence

```text
1. create G8 + G7
2. start G8 → archive
3. start G7 → archive
4. 父 AC 勾选 → archive 父
```

## Child create

```bash
py -3 ./.trellis/scripts/task.py create "热噪声通道 nbar" --slug cvsim-thermal-channel --description "G8: loss nbar for G/B; Y=(1-T)(nbar+1/2)"
py -3 ./.trellis/scripts/task.py create "Fock two_mode_squeeze" --slug cvsim-fock-s2 --description "G7: Fock S2 2-mode; align G sinh^2 r"
```

## Validation

```bash
.venv\Scripts\python.exe -m pytest tests -q
.venv\Scripts\python.exe -m cvsim.demos.user_acceptance
```
