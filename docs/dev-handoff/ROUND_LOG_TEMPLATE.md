# Round Log Template

复制以下模板到 `PHASE_LOG.md` 末尾，并按本轮实际情况填写。

```markdown
## Phase <phase-name>: <short-title>

- 日期：
- 执行 Agent：
- 任务目标：
- 修改文件：
  - `<path>`
- 行为变化：
  - 是/否：
  - 说明：
- 测试命令：
  - `<command>`
- 测试结果：
  - `<result>`
- 提交 hash：
  - `<hash> <message>`
- 风险备注：
  - `<risk>`
- 下一步建议：
  - `<next-step>`
- 是否停止等待验收：
  - 是/否
```

填写要求：

- 如果没有提交，提交 hash 填“未提交，等待验收”。
- 如果没有运行测试，必须说明原因。
- 如果修改涉及安全、权限、外部请求、DB、Job、Queue、下载、路径、密钥，风险备注必须写清楚。
- 如果本轮是只读评估，修改文件填“无”，行为变化填“否”。
