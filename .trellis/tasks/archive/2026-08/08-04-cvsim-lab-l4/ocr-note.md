# OCR review 降级记录（e28767a, ec9b3c7）

`ocr review` 对本次两个 commit 全部失败（failed/aborted/partial 0 findings）：
- 现象：llm test 通过（provider:review → localhost:20128/v1, glm-5.2），但 review 并发请求全挂
- 尝试：--concurrency 1、--timeout 20、--exclude 缩小范围、--format json、nohup 后台 —— 均失败/静默退出
- 对比：L3 的 685e25a 曾 complete（4/6 comments）→ 本地 LLM 代理当前不稳定，非配置错误
- 降级：改派 reviewer 子代理独立审查 diff（保留 3.4 独立审查意图）；待代理恢复后可补跑 ocr review
