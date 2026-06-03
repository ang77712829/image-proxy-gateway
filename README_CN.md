# Image Proxy Gateway：给 Agent 接上图片生成能力

> 面向 AI Agent、NAS、New-API 和自托管工作流的本地图片生成网关。默认内置硅基流动、魔搭、Pollinations 三个渠道，对外提供兼容 OpenAI Images 的统一接口。

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-ready-009688.svg)](https://fastapi.tiangolo.com/)

---

## 先看结论

这个项目解决的是一个很实际的问题：让 Agent 只调用一个接口，就能使用多个图片生成渠道。

```text
AI Agent / New-API / OpenAI SDK
        ↓
POST http://你的服务器:9890/v1/images/generations
        ↓
Image Proxy Gateway
        ↓
硅基流动 Kolors → 魔搭 Qwen / FLUX / Z-Image → Pollinations 兜底
        ↓
返回图片 URL 或 b64_json
```

默认降级链：

```text
kolors → qwen → flux → z-image → z-turbo → pollinations
```

付费渠道，比如 `gpt-image-2` / `openai-image`，已经预留，但**不会进入默认降级链**，避免误消耗付费额度。

---

## 新用户最先要做什么

默认三个图片渠道已经写进代码里了，不需要改代码，只需要把密钥填进 `.env`。

### 推荐配置顺序

| 顺序 | 渠道 | 是否建议配置 | 作用 |
|---|---|---|---|
| 1 | 硅基流动 SiliconFlow | 强烈建议 | 启用 `kolors` 主力通道 |
| 2 | 魔搭 ModelScope | 建议 | 启用 `qwen`、`flux`、`z-image`、`z-turbo` |
| 3 | Pollinations | 可选 | 不填也能尝试公共兜底，填了可走新版接口 |

最少配置方式：**只填 `SILICONFLOW_API_KEY` 或 `MODELSCOPE_API_KEY` 其中一个就能启动测试**。如果两个都填，体验更稳。

---

## 三个默认渠道怎么注册和拿 Key

### 1. 硅基流动 SiliconFlow

- 注册入口：`https://cloud.siliconflow.cn`
- 官方快速开始文档：`https://docs.siliconflow.cn/en/userguide/quickstart`
- 需要填写的变量：`SILICONFLOW_API_KEY`
- 启用的模型别名：`kolors` / `siliconflow`

获取步骤：

1. 打开 `https://cloud.siliconflow.cn` 注册并登录。
2. 进入控制台的 **API Keys** 页面。
3. 点击创建密钥。
4. 复制生成的密钥，填入 `.env`：

```env
SILICONFLOW_API_KEY=你的硅基流动密钥
```

说明：官方文档里写的是进入 API Keys 页面后创建 API Key；具体额度、价格、免费规则会变，以控制台和价格页为准。

### 2. 魔搭 ModelScope

- 注册入口：`https://modelscope.cn`
- API-Inference 介绍：`https://modelscope.cn/docs/model-service/API-Inference/intro`
- 使用限制说明：`https://modelscope.cn/docs/model-service/API-Inference/limits`
- 需要填写的变量：`MODELSCOPE_API_KEY`
- 启用的模型别名：`qwen`、`flux`、`z-image`、`z-turbo`

获取步骤：

1. 打开 `https://modelscope.cn` 注册并登录。
2. 进入个人中心，找到 **访问令牌 / Access Token**。
3. 创建一个新令牌并复制。
4. 填入 `.env`：

```env
MODELSCOPE_API_KEY=你的魔搭访问令牌
```

说明：魔搭官方 API-Inference 是面向注册用户的免费推理服务。我们实测图片生成通道按所有图片模型共享约 50 张/天做本地保护，所以默认：

```env
MODELSCOPE_DAILY_LIMIT=50
```

真实额度仍以魔搭平台返回为准。

### 3. Pollinations

- 官网：`https://pollinations.ai`
- 密钥入口：`https://enter.pollinations.ai`
- API 文档：`https://github.com/pollinations/pollinations/blob/main/APIDOCS.md`
- 需要填写的变量：`POLLINATIONS_API_KEY`
- 启用的模型别名：`pollinations`

用法：

- 不填 `POLLINATIONS_API_KEY`：网关会尝试旧公共图片接口，作为最后兜底。
- 填写 `POLLINATIONS_API_KEY`：优先走新版 OpenAI-compatible 图片接口。

```env
POLLINATIONS_API_KEY=你的 Pollinations 密钥
```

---

## 快速开始

```bash
git clone https://github.com/ang77712829/image-proxy-gateway.git
cd image-proxy-gateway

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env，至少填写 SILICONFLOW_API_KEY 或 MODELSCOPE_API_KEY 其中一个

python3 scripts/proxy.py
```

健康检查：

```bash
curl http://localhost:9890/health
```

生成图片：

```bash
curl -X POST http://localhost:9890/v1/images/generations   -H "Content-Type: application/json"   -d '{"prompt":"一只戴墨镜的猫，赛博朋克风格"}'
```

指定模型：

```bash
curl -X POST http://localhost:9890/v1/images/generations   -H "Content-Type: application/json"   -d '{"model":"qwen","prompt":"夕阳下的山脉","size":"1024x1024"}'
```

如果配置了 `GATEWAY_API_KEY`：

```bash
curl -X POST http://localhost:9890/v1/images/generations   -H "Authorization: Bearer 你的网关访问密钥"   -H "Content-Type: application/json"   -d '{"model":"z-turbo","prompt":"电影光感人像写真"}'
```

---

## 完整 `.env` 示例

```env
# 硅基流动：启用 kolors 主力通道
SILICONFLOW_API_KEY=你的硅基流动密钥

# 魔搭：启用 qwen / flux / z-image / z-turbo
MODELSCOPE_API_KEY=你的魔搭访问令牌

# Pollinations：可选，不填也会尝试公共兜底
POLLINATIONS_API_KEY=

# 可选付费图片渠道：显式指定 gpt-image-2 / openai-image 时才会调用
OPENAI_IMAGE_API_KEY=
OPENAI_IMAGE_BASE_URL=https://api.openai.com/v1
OPENAI_IMAGE_MODEL=gpt-image-2

# 网关访问密钥，局域网多人或公网部署时建议填写
GATEWAY_API_KEY=换成一个足够长的随机字符串

PROXY_HOST=0.0.0.0
PROXY_PORT=9890
PUBLIC_BASE_URL=http://你的服务器IP:9890
IMAGE_PROXY_STATE_DIR=/data
MODELSCOPE_DAILY_LIMIT=50
POLLINATIONS_MODEL=zimage
HTTP_TIMEOUT=60
MAX_POLL_TIME=120
POLL_INTERVAL=3
```

---

## 后台运行

### Docker Compose

```bash
cp .env.example .env
# 编辑 .env，填好密钥
docker compose -f templates/docker-compose.yml up -d --build
```

查看日志：

```bash
docker compose -f templates/docker-compose.yml logs -f
```

### systemd

创建服务文件：

```bash
sudo tee /etc/systemd/system/image-proxy-gateway.service > /dev/null <<'EOF'
[Unit]
Description=Image Proxy Gateway
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/image-proxy-gateway
EnvironmentFile=/opt/image-proxy-gateway/.env
ExecStart=/opt/image-proxy-gateway/.venv/bin/python /opt/image-proxy-gateway/scripts/proxy.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now image-proxy-gateway
sudo systemctl status image-proxy-gateway
```

---

## 接入 Agent / New-API

### 通用 Agent

让 Agent 调用：

```text
POST http://你的服务器IP:9890/v1/images/generations
```

请求体示例：

```json
{
  "model": "qwen",
  "prompt": "增强后的最终提示词",
  "size": "1024x1024",
  "response_format": "url"
}
```

建议把 `SKILL.md` 放进 Agent 的技能目录，让 Agent 学会：

1. 先理解用户意图；
2. 自动选择模型别名；
3. 扩写或润色提示词；
4. 再调用网关。

### OpenClaw / Hermes

不同 Agent 的技能目录不一样，不建议文档写死某个路径。通用做法是：

1. 把 `SKILL.md` 放到该 Agent 的技能目录；
2. 在 Agent 的工具配置里写入网关地址；
3. 如果配置了 `GATEWAY_API_KEY`，把它作为工具密钥保存；
4. 让 Agent 调用 `/v1/images/generations`。

### New-API

新增一个 OpenAI-compatible 渠道：

```text
Base URL: http://你的服务器IP:9890
API Key: 如果配置了 GATEWAY_API_KEY，就填这个值
模型：kolors, qwen, flux, z-image, z-turbo, pollinations, gpt-image-2
```

---

## 模型别名

| 别名 | 渠道 | 实际模型 | 推荐场景 |
|---|---|---|---|
| `kolors` | 硅基流动 | `Kwai-Kolors/Kolors` | 通用文生图、中英文提示词、默认主力通道 |
| `siliconflow` | 硅基流动 | 同 `kolors` | 兼容别名，建议新请求用 `kolors` |
| `qwen` | 魔搭 | `Qwen/Qwen-Image-2512` | 中文海报、带字图片、复杂指令、二次元/插画 |
| `flux` | 魔搭 | `black-forest-labs/FLUX.1-Krea-dev` | 摄影感、自然光、产品氛围图、风景 |
| `z-image` | 魔搭 | `Tongyi-MAI/Z-Image` | 创意艺术、超现实概念、多样构图 |
| `z-turbo` | 魔搭 | `Tongyi-MAI/Z-Image-Turbo` | 写实人像、商业摄影、快速出图 |
| `pollinations` | Pollinations | 默认 `zimage` | 最后兜底和轻量测试 |
| `gpt-image-2` | 兼容 OpenAI 图片接口 | 通过 `OPENAI_IMAGE_MODEL` 配置 | 显式付费路由，不在默认链中 |

---

## API

### 生成图片

```http
POST /v1/images/generations
```

请求体：

```json
{
  "model": "qwen",
  "prompt": "赛博朋克城市夜景，电影光感",
  "size": "1024x1024",
  "response_format": "url"
}
```

`response_format` 支持：

- `url`
- `b64_json`

当前每次请求返回一张图片。

### 健康检查

```http
GET /health
```

返回网关状态、已配置渠道、本地配额计数器、公开访问地址和可用模型别名。

### 模型列表

```http
GET /v1/models
```

返回 OpenAI 风格的模型列表。

---

## 常见问题

### 只配置一个密钥可以用吗？

可以。至少配置 `SILICONFLOW_API_KEY` 或 `MODELSCOPE_API_KEY` 其中一个即可。两个都配置会更稳。

### Pollinations 不填密钥还能用吗？

可以尝试。网关会使用旧公共图片接口做最后兜底，但稳定性、限流和可用性不承诺。需要更稳定时建议配置 `POLLINATIONS_API_KEY`。

### 图片链接打不开怎么办？

检查 `PUBLIC_BASE_URL`。如果 Agent 和网关不在同一台机器，不能用默认的 `http://localhost:9890`，应该改成网关机器的局域网地址，例如：

```env
PUBLIC_BASE_URL=http://192.168.1.10:9890
```

### 端口 9890 被占用了怎么办？

修改：

```env
PROXY_PORT=9891
PUBLIC_BASE_URL=http://你的服务器IP:9891
```

### 魔搭返回 403 / 401 怎么办？

优先检查：

1. `MODELSCOPE_API_KEY` 是否填错；
2. 令牌是否过期；
3. 账号是否能正常访问 API-Inference；
4. 模型是否临时下线或额度已用尽。

### 生成很慢正常吗？

正常。图片生成通常需要几秒到几十秒。魔搭是异步任务，网关会提交任务后轮询结果。

### 怎么查看本地额度保护计数？

访问：

```bash
curl http://localhost:9890/health
```

里面会显示魔搭本地保护计数。注意这不等于平台真实余额，只是本地保护值。

### 可以公网开放吗？

可以，但必须配置 `GATEWAY_API_KEY`，并建议放在 Nginx/Caddy 后面启用 HTTPS、限流和访问日志。

---

## 扩展新渠道

当前代码已经是 Provider Registry 架构。新增渠道时，不要在主流程里堆 `if/else`，应该新增一个 provider adapter，然后注册模型别名。

预留方向：

- 即梦；
- 兼容 OpenAI 的 GPT 图片模型；
- 自建 ComfyUI；
- 其他第三方图片服务。

开发说明见 `DEVELOPMENT.md`。

---

---

## Agnes 图片/视频能力

Agnes 属于显式调用渠道，不进入默认降级链。

- 图片别名：`agnes-image`、`agnes-2.1`、`agnes-2.0`
- 视频入口：`POST /v1/videos`、`GET /v1/videos/{task_id}`
- 图片能力示例：`docs/AGNES_IMAGE_CALL_EXAMPLES.md`
- 视频能力示例：`docs/AGNES_VIDEO_CALL_EXAMPLES.md`
- 总索引：`docs/AGNES_MODEL_CALL_EXAMPLES.md`

如果使用 Agnes，请在 `.env` 中填写：

```env
AGNES_API_KEY=你的 Agnes 密钥
AGNES_BASE_URL=https://apihub.agnes-ai.com/v1
AGNES_IMAGE_MODEL=agnes-image-2.1-flash
```

注意：Agnes 是否免费、额度多少、具体字段名和模型名，以 Agnes 官方文档和后台为准。

## License

MIT
