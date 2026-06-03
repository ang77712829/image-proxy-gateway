# 开发说明

本文档给维护者和后续 Agent 使用，普通用户优先看 `README.md`。

## 设计原则

Image Proxy Gateway 的代码结构遵循一个原则：

> 对上游保持一个统一的 OpenAI-compatible 接口，对下游用 Provider Registry 接不同图片平台。

这样以后新增即梦、GPT 图片模型、自建 ComfyUI 或其他图片服务时，不需要改动上游调用方式。

## Provider Registry

每个图片渠道都应该独立封装成 provider adapter，并实现统一的 `generate()` 方法。

当前默认渠道：

- `SiliconFlowProvider`：硅基流动 Kolors；
- `ModelScopeProvider`：魔搭 Qwen / FLUX / Z-Image / Z-Turbo；
- `PollinationsProvider`：Pollinations 兜底；
- `OpenAICompatibleImageProvider`：兼容 OpenAI 图片接口的可选付费渠道。

新增渠道时建议补齐：

1. 渠道名称；
2. 环境变量；
3. 真实模型名；
4. 网关别名；
5. 请求参数映射；
6. 响应格式标准化；
7. 错误分类；
8. 是否需要本地缓存远程图片；
9. `/health` 状态；
10. README、README_CN、SKILL、.env.example 同步更新。

## 默认渠道和付费渠道

默认降级链只包含免费或轻量兜底渠道：

```text
kolors → qwen → flux → z-image → z-turbo → pollinations
```

`gpt-image-2` / `openai-image` 这类付费渠道必须显式调用，不应该进入默认链，避免普通请求误消耗付费额度。

## 魔搭异步任务头

魔搭图片任务提交和轮询阶段使用不同任务类型值：

```env
MODELSCOPE_SUBMIT_TASK_TYPE=text-to-image-generation
MODELSCOPE_POLL_TASK_TYPE=image_generation
```

这两个值不要因为名字不同就合并。提交阶段标识任务来源，轮询阶段查询统一的图片生成任务记录。

## 本地缓存策略

如果后端返回的是临时图片 URL，建议下载到本地 `OUTPUT_DIR`，再通过：

```text
/generated/文件名
```

对外提供。这样 NAS、Agent、New-API 访问会更稳定。

## 提交前检查

```bash
python3 -m py_compile scripts/proxy.py
git ls-files | grep -E 'blog-draft|cache|__pycache__|\.pyc'
```

第二条命令没有输出才算干净。
