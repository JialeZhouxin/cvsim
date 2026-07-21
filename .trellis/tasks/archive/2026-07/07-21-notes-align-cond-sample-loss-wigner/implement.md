# Implement · notes align

## Preconditions

- [x] 用户批准
- [x] `task.py start`

## Checklist

1. [x] 02 G
2. [x] 01 F
3. [x] 03 B
4. [x] 术语表 + README
5. [x] 04 指针
6. [x] 禁词自检
7. [x] commit/finish

## Validation

```bash
# ban words in theory notes (exclude cvsim/, .trellis/)
rg -n "cvsim|GaussianState|homodyne_|FockDensity|BosonicState" --glob "*.md" -g "!cvsim/**" -g "!.trellis/**"

# optional: suite still green
.venv\Scripts\python.exe -m pytest tests -q
```

## Risks

| 风险 | 缓解 |
|------|------|
| ħ=2 文献数混入 | 正文钉 1/π 与 I/2 |
| 写穿 API | ban list + AC-N5 |
| 04 膨胀 | 只指针 |
