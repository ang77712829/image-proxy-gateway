# Agent Handoff Rules

本目录是 AngeMedia Gateway v0.2.0 开发期内部协作日志，供 Codex、CC、mimo 等 Agent 交接使用。它不是 README、SKILL 或发布文档。

## 开始前必读

所有 Agent 开始任何任务前，必须先读取：

- `docs/dev-handoff/AGENT_RULES.md`
- `docs/dev-handoff/CURRENT_STATE.md`
- `docs/dev-handoff/PHASE_LOG.md`
- `docs/dev-handoff/NEXT_TASK.md`
- `docs/dev-handoff/ROUND_LOG_TEMPLATE.md`

开始前必须执行并确认：

```powershell
git status --short --branch
```

如果工作区有未提交改动，必须先判断是否属于上一轮已验收但未提交内容，不能覆盖或回滚其他 Agent/用户改动。

## 执行规则

- 一个任务只做已批准范围。
- 不允许顺手优化。
- 不允许改无关文件。
- 不允许提前进入下一阶段。
- 不允许在低风险任务中引入大范围统一抽象。
- 不允许把测试便利改成生产代码变化。
- 高风险任务必须先给计划，不直接改代码。
- 涉及权限、密钥、外部请求、下载、路径、DB、Job、Queue、前端结构的任务都视为高风险。

## 输出要求

每轮完成后必须输出：

- `git diff --name-only`
- `git diff --stat`
- 修改摘要
- 测试结果
- 风险说明
- 是否更新了交接日志

如果有提交，还必须记录提交 hash。

## Agent 分工建议

- Codex 适合高风险、复杂、多文件、需要严格边界和回归验证的任务。
- CC + mimo 适合低中风险小任务，例如只读评估、小范围测试补充、轻量 service wrapper 迁移、文档日志维护。
- 不论由哪个 Agent 执行，每轮都必须更新 `PHASE_LOG.md` 和 `NEXT_TASK.md`，除非该轮明确是只读评估且用户要求不修改任何文件。

## 禁止跨阶段行为

未经明确批准，不得开始：

- LLM Copilot
- 统一 LLM Client
- 重试策略
- Job / DB / Queue
- Web Studio 重构
- 前端框架迁移
- README / SKILL / 发布文档修改
