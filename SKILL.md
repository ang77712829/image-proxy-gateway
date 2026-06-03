---
name: image-proxy-gateway
description: "当用户表达生成图片、画图、文生图、生成封面/海报/头像，或需要安装本地图片网关时使用；需要文生视频/图生视频时只索引到独立示例文档，不在本技能展开平台细节。"
version: v0.2
author: 安歌 & 辰辰
license: MIT
metadata:
  hermes:
    tags: [image-generation, openai-compatible, ai-agent, prompt-routing, model-routing]
    related_skills: [ai-media-api-research]
---

# Image Proxy Gateway 技能

## 先判断用户处在哪一步

1. **首次安装 / 配置网关**：只执行最小安装流程。密钥注册、后台运行、Docker、systemd、New-API 接入以 `README.md` 为准。
2. **网关已运行 / 直接生图**：先做模型路由和提示词增强，再调用 `/v1/images/generations`。
3. **文生视频 / 图生视频**：不要把视频长文档塞进本技能。视频调用方式见 `docs/AGNES_VIDEO_CALL_EXAMPLES.md`，总索引见 `docs/AGNES_MODEL_CALL_EXAMPLES.md`，视频适配代码在 `adapters/agnes_video.py`。
4. **Agnes 高级图片能力**：Agnes 的文生图、图生图、多图参考、局部重绘等详细示例见 `docs/AGNES_IMAGE_CALL_EXAMPLES.md`。
5. **开发或新增渠道**：转到 `DEVELOPMENT.md` 或独立适配文档。

## 首次安装最小流程

当用户说“安装这个技能”“部署图片网关”“让 Agent 能画图”，执行最小流程：

```bash
git clone https://github.com/ang77712829/image-proxy-gateway.git
cd image-proxy-gateway

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 编辑仓库根目录 .env，至少填写 SILICONFLOW_API_KEY 或 MODELSCOPE_API_KEY 其中一个

python3 scripts/proxy.py
```

如果当前包使用 OpenClaw 工作区结构，入口可能是：

```bash
python3 scripts/image-gateway/gateway.py
```

验证：

```bash
curl http://localhost:9890/health
```

程序会优先读取仓库根目录的 `.env`。注册密钥、后台运行、开机自启、Docker Compose、New-API 接入，请转 `README.md`。

## 配置优先级

默认三个图片渠道已经集成在代码里，用户不需要改代码，只需要填环境变量：

1. 优先配置 `SILICONFLOW_API_KEY`，启用 `kolors` 主力通道。
2. 建议配置 `MODELSCOPE_API_KEY`，启用 `qwen` / `flux` / `z-image` / `z-turbo`。
3. `POLLINATIONS_API_KEY` 可不填；不填时网关会尝试公共兜底通道。
4. `AGNES_API_KEY`、`OPENAI_IMAGE_*`、`JIMENG_*` 是可选/预留渠道，不进入默认免费降级链。

密钥注册地址、额度口径和完整配置示例以 `README.md` 和 `.env.example` 为准。

## 网关接口

默认图片接口：

```text
POST http://<网关地址>:9890/v1/images/generations
```

如果配置了 `GATEWAY_API_KEY`，请求要带：

```http
Authorization: Bearer <GATEWAY_API_KEY>
```

或：

```http
X-API-Key: <GATEWAY_API_KEY>
```

## 模型别名

| 别名 | 渠道 | 实际模型 | 推荐场景 |
|---|---|---|---|
| `kolors` | 硅基流动 | `Kwai-Kolors/Kolors` | 通用文生图、中英文提示词、默认主力通道 |
| `siliconflow` | 硅基流动 | 同 `kolors` | 兼容别名，新请求优先用 `kolors` |
| `qwen` | 魔搭 | `Qwen/Qwen-Image-2512` | 中文海报、带字图片、复杂指令、二次元/插画 |
| `flux` | 魔搭 | `black-forest-labs/FLUX.1-Krea-dev` | 摄影感、自然光、产品氛围图、风景 |
| `z-image` | 魔搭 | `Tongyi-MAI/Z-Image` | 创意艺术、超现实概念、多样构图 |
| `z-turbo` | 魔搭 | `Tongyi-MAI/Z-Image-Turbo` | 写实人像、商业摄影、快速出图 |
| `pollinations` | Pollinations | 默认 `zimage` | 最后兜底和轻量测试 |
| `agnes-image` / `agnes-2.1` | Agnes AI | `agnes-image-2.1-flash` | 显式调用，图片效果优先用 2.1 |
| `agnes-2.0` | Agnes AI | `agnes-image-2.0-flash` | 显式调用，兼容 2.0 |
| `gpt-image-2` / `openai-image` | 兼容 OpenAI 图片接口 | 由 `OPENAI_IMAGE_MODEL` 配置 | 显式付费路由，不进入默认链 |

未指定模型时默认降级链：

```text
kolors → qwen → flux → z-image → z-turbo → pollinations
```

## Agent 生图流程

1. **判断图片类型**：写实人像、二次元/插画、中文海报、产品图、风景、创意艺术，还是普通通用图。
2. **提取硬约束**：保留主体、场景、风格、用途、尺寸、图片中文字、负面限制；例如“不要人物”“不要水印”“不要文字”不能丢。
3. **选择模型**：写实人像用 `z-turbo`；二次元/中文海报用 `qwen`；产品氛围/风景用 `flux`；创意艺术用 `z-image`；普通通用图可省略 `model` 走默认链；明确要 Agnes 图片效果可用 `agnes-2.1`；明确付费高质量才用 `gpt-image-2`。
4. **决定扩写强度**：短提示词强扩写；中等描述补细节；已经很完整时只轻度润色，不改变原意。
5. **按模板组织最终提示词**：

```text
[风格]，[主体]，[场景环境]，[光影氛围]，[镜头/构图]，[材质/细节]，[用途/比例/画质要求]。
不要：[负面限制]
```

如果用户要求图片里出现文字，必须补充：文字原文、位置、字体风格、层级、留白和可读性。

6. **调用网关**：发送增强后的 prompt 和模型别名。客户端打不开 URL 时，改用 `response_format: "b64_json"`。
7. **失败后复用增强提示词重试**：不要让用户重复描述原始需求；优先换模型、调整风格词、加强主体描述或降低复杂度。

## 结果返回与后处理

- 网关返回 `data[0].url` 或 `data[0].b64_json` 后，先确认图片能被当前客户端访问。
- 图片如何作为文件/媒体消息发送，由当前宿主 Agent 或平台决定。
- 可以提示 Hermes、OpenClaw 或其他宿主 Agent 去查自己的官方“图片/文件发送”规范；本技能不硬编码任何平台发送语法。
- 不要在本技能里写死飞书、Discord、Telegram、微信、QQ 等渠道专用格式。
- 用户不满意图片时，优先说明会保留原意并调整模型或提示词，而不是让用户从头再说一遍。

## 最小请求示例

中文封面图，优先 `qwen`：

```json
{
  "model": "qwen",
  "prompt": "现代科技风中文公众号封面，深蓝色未来感背景，中心是发光的 AI 图片网关枢纽图标，周围有模型路由线条和图片卡片。标题文字：『给 AI Agent 接上文生图』，标题位于上方居中，粗体中文字体，高对比度，留白充足，4:3 构图，不要人物，不要水印。",
  "size": "1024x1024",
  "response_format": "url"
}
```

写实人像/摄影感，优先 `z-turbo`：

```json
{
  "model": "z-turbo",
  "prompt": "写实电影感人像摄影，一位成年女性模特站在雨夜城市街头，霓虹灯和湿润路面反射在背景中，柔和轮廓光，自然皮肤质感，85mm 镜头感，浅景深，半身构图，高级商业摄影风格。不要：文字、水印、夸张塑料感。",
  "size": "1024x1024",
  "response_format": "url"
}
```

Agnes 图片 2.1，显式调用：

```json
{
  "model": "agnes-2.1",
  "prompt": "高级产品摄影，一台极简白色无线音箱放在石材桌面上，柔和自然光，浅景深，干净背景，商业广告质感。不要：文字、水印、杂乱背景。",
  "size": "1024x1024",
  "response_format": "url"
}
```

## Agnes 能力文档索引

- Agnes 图片能力详解：`docs/AGNES_IMAGE_CALL_EXAMPLES.md`
- Agnes 视频能力详解：`docs/AGNES_VIDEO_CALL_EXAMPLES.md`
- Agnes 总索引：`docs/AGNES_MODEL_CALL_EXAMPLES.md`
- 视频提交默认只返回 `task_id`，调用方需要继续请求 `GET /v1/videos/{task_id}` 轮询结果；同步等待只在明确需要时使用 `wait_for_completion=true`
- 视频代码入口：`scripts/image-gateway/adapters/agnes_video.py`
- 这些文档展开讲调用方式；本技能主体只保留运行时需要的最小规则。

## 失败处理

- `/health` 连不上：提示用户检查网关是否启动、端口是否正确、是否在另一台机器上运行。
- 401：检查 `GATEWAY_API_KEY` 和请求头。
- 502：所有后端都失败，查看错误摘要，检查密钥、额度或临时切换模型。
- 配额耗尽：提示等待次日重置、配置其他渠道或显式切换模型。
- 返回本地图片 URL 但客户端打不开：检查 `PUBLIC_BASE_URL` 是否是客户端能访问的地址，或改用 `b64_json`。
- 报错时只总结渠道问题，不要暴露任何密钥。

## 常见错误

- 网关没启动就直接调用生图接口。
- 把 `qwen`、`flux`、`z-turbo` 当成真实模型 ID 直接传给后端；它们只是网关别名。
- 直接裸传用户一句话，没有扩写提示词。
- 用户已经写得很完整时还乱加新主体。
- 普通请求误用 `gpt-image-2` 这类付费别名。
- 把魔搭本地计数器当成真实余额；本地计数只是保护值，真实额度以平台返回为准。
- 新请求优先用 `kolors`，`siliconflow` 只是兼容别名。
