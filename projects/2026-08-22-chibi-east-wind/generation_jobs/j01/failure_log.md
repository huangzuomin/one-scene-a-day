# Failure Log · j01

- **时间**：2026-08-22
- **操作**：submit_run.py 提交 prompt.txt
- **结果**：失败，exit=1
- **错误**：`错误码: 2, 错误信息: Ak已过期,请更换`
- **诊断**：XYQ_ACCESS_KEY 鉴权过期，非任务本身问题；简报内容已就绪无需修改
- **恢复条件**：用户更新 XYQ_ACCESS_KEY 后，从 Step 8 原样重新提交（断点续跑，Step 1~6 产物全部有效）
