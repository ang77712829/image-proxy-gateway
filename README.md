# AngeMedia API 模式

[English](README.md) | [简体中文](README_CN.md)

> OpenAI-compatible image and video generation gateway for AI Agents, NAS, New-API, and self-hosted workflows.

AngeMedia is the media-generation sibling of AngeVoice. It focuses on images, video, model routing, prompt enhancement, and stable local media delivery.

## What it does

```text
AI Agent / New-API / OpenAI SDK / AngeMedia Studio
        ↓
AngeMedia Gateway
        ↓
SiliconFlow Kolors → ModelScope Qwen / FLUX / Z-Image
        ↓
Agnes image/video and OpenAI-compatible image providers when explicitly selected
        ↓
Stable local /generated/ URL
```

## Highlights

- OpenAI-compatible image endpoint: `POST /v1/images/generations`
- Video task endpoints: `POST /v1/videos`, `GET /v1/videos/{task_id}`
- Built-in media localization: temporary remote URLs are downloaded into `/generated/`
- Lightweight route API: `POST /v1/media/route`
- Agent Skill docs for image/video generation, routing, and prompt guidance
- Built-in AngeMedia Studio web UI at `/`
- Provider catalog API: `GET /v1/admin/catalog` — returns all built-in providers, models, capabilities, params, and size presets (admin-auth required)

## Default image chain

```text
kolors → qwen → flux → z-image → z-turbo
```

Optional explicit providers:

- `agnes-image`, `agnes-2.1`, `agnes-2.0`
- `gpt-image-2`, `openai-image`
- `agnes-video-v2.0` through `/v1/videos`
- `pollinations` (experimental, disabled by default — not part of the fallback chain)

## Quick start

```bash
git clone https://github.com/ang77712829/angemedia-gateway.git
cd angemedia-gateway

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
python3 scripts/proxy.py
```

Or use uvicorn directly:

```bash
python -m uvicorn scripts.angemedia_gateway.server:app --host 127.0.0.1 --port 9890
```

Open:

```text
http://localhost:9890/
```

Health check:

```bash
curl http://localhost:9890/health
```

## Configuration

Fill at least one of these in `.env`:

```env
SILICONFLOW_API_KEY=
MODELSCOPE_API_KEY=
POLLINATIONS_API_KEY=
```

Optional:

```env
AGNES_API_KEY=
OPENAI_IMAGE_API_KEY=
OPENAI_IMAGE_BASE_URL=https://api.openai.com/v1
OPENAI_IMAGE_MODEL=gpt-image-2
GATEWAY_API_KEY=
ANGE_LLM_API_KEY=
ANGE_LLM_BASE_URL=https://api.openai.com/v1
ANGE_LLM_MODEL=gpt-4o-mini
```

For full Chinese setup instructions, see `README_CN.md`.

## API quick examples

Generate image:

```bash
curl -X POST http://localhost:9890/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{"prompt":"a cinematic orange cat wearing sunglasses, neon city background","size":"1024x1024"}'
```

Submit video task:

```bash
curl -X POST http://localhost:9890/v1/videos \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A cinematic shot of a cat walking through a neon rainy street","num_frames":121,"frame_rate":24}'
```

Route before generation:

```bash
curl -X POST http://localhost:9890/v1/media/route \
  -H "Content-Type: application/json" \
  -d '{"prompt":"画一张现实风格的美女写真"}'
```

## Skill docs

- Main skill index: `SKILL.md`
- Image generation: `docs/SKILL_IMAGE_GENERATION.md`
- Video generation: `docs/SKILL_VIDEO_GENERATION.md`
- Routing: `docs/SKILL_MEDIA_ROUTING.md`
- Prompt guidance: `docs/SKILL_PROMPT_ENHANCEMENT.md`
- Agnes examples: `docs/AGNES_MODEL_CALL_EXAMPLES.md`

## Web Studio

v0.2.0 provides a minimal Web Studio for basic administration:

**Entry points:**

- Studio: `GET /` or `GET /studio`
- Redirect: `GET /admin` → `/#/dashboard`
- Redirect: `GET /admin/` → `/#/dashboard`

**Features:**

- Dashboard: health/session summary
- Generate Image: prompt input with provider selection
- Generate Video: catalog-aware minimal video submission page (fetches providers/models/capabilities from `/v1/admin/catalog`)
- Jobs: list view of generation jobs
- Assets: list view of generated/uploaded assets with thumbnails
- Providers: minimal onboarding (create/enable/disable)
- API Keys: list/create/revoke for API mode

**Admin login:**

```text
username: admin
password: admin123456
```

The password is stored as a PBKDF2 hash in SQLite, not as plaintext. Change it immediately after first login in production.

```env
ADMIN_USERNAME=admin
ADMIN_DEFAULT_PASSWORD=admin123456
ADMIN_COOKIE_SECURE=false
```

## Provider onboarding (minimal)

1. Login to Web Studio at `http://localhost:9890/`
2. Navigate to "Providers" (服务商)
3. Click "Create Provider"
4. Select `openai_image` provider type
5. Fill: name, base_url, default_model, api_key
6. Enable the provider
7. Navigate to "Generate Image" (生成图片)
8. Select your custom provider from dropdown
9. Enter prompt and submit

**Current scope:** Provider create and enable/disable only. Provider test/status/delete/sort/edit UI is not yet implemented.

## Jobs and Assets

- **Jobs:** View list of generation jobs with status, type, duration
- **Assets:** View list of generated/uploaded assets with thumbnails

Both are read-only list views. Detail pages and full management UI are planned for future releases.

## Security notes

- **Admin API:** Uses HttpOnly session cookie authentication
- **API mode API Keys:** Used for `/v1/images/generations` and other generation endpoints
- **API Key boundary:** API mode API Keys cannot access Admin API endpoints
- **File access:** `/generated` and `/uploads` require authentication
- **Health endpoint:** `/health` returns minimal `{"status":"ok"}` (no secrets)
- **Request hash:** Generation requests include dedupe/admission via request_hash
- **Secrets protection:** Provider secrets, raw URLs, and sensitive data are not exposed in Web Studio summaries

## Current limitations (v0.2.0)

The following features are not yet implemented:

- Full Provider management (test/status/delete/sort/edit)
- Provider fallback chain UI
- AI Assistant (WIP / disabled — backend exists but no public routes, not part of v0.2.0 stable)
- Worker/Queue/job_events UI
- Multi-user/SaaS/billing/quota
- Old admin restoration
- v0.1 data migration/backfill
- Google provider support
- Model override UI
- Runtime routing is not yet fully catalog-driven (catalog YAML exists and is exposed via API, but `routing.py` still uses hardcoded `DEFAULT_CHAIN`)
- Video ref_inputs upload (catalog declares ref_inputs; the Generate Video page shows them as read-only "coming soon")

## Legacy v0.1.0 reference

v0.1.0 had a broader legacy UI and more old user-facing controls. It remains useful as a reference for users who specifically need the old local-only experience, but it does not share the v0.2.0 security boundaries and Web Studio architecture.

For new deployments, v0.2.0 is the recommended baseline. Use any legacy v0.1.0 README or release archive only with the security trade-offs understood. The `v0.1.0` tag is available in the repository for historical reference.

## Version

AngeMedia Gateway v0.2.0 - Core-Safe + Minimal Web Studio + Minimal Provider Onboarding + Catalog-Aware Generate Video

The previous experimental name was Image Proxy Gateway. There is no compatibility promise for the old name because the project had no public users yet.

v0.2.0 focuses on safe foundation, minimal usable Web Studio, and catalog-aware video generation. v0.2.x will recover more user-facing experience.

## License

MIT

## Modular backend layout

The compatibility entry remains:

```text
scripts/proxy.py
```

The real backend implementation lives in:

```text
scripts/angemedia_gateway/
```

This splits configuration, configuration metadata, SQLite state, schemas, media localization, routing, assistant logic, providers, and FastAPI route assembly. `server.py` only assembles the app; page, admin, media, and storage routes live under `scripts/angemedia_gateway/routes/`.

## Standalone Agent Skill package

Agent-facing skill files live in:

```text
skill/
```

This keeps the agent skill small and focused on image/video generation calls, without loading the full web/admin/project documentation.

Release workflow builds both:

```text
angemedia-gateway-<version>.zip
angemedia-gateway-skill-<version>.zip
```

## Security note: GATEWAY_API_KEY

When `GATEWAY_API_KEY` is empty, AngeMedia allows local/LAN clients to call image and video generation APIs without an API key. This is intentional for self-hosted local deployments.

For public deployments, always configure `GATEWAY_API_KEY`, use HTTPS reverse proxy protection, and change the default admin password.

- `UPLOAD_MAX_FILES` controls how many files `/v1/uploads` accepts in one request; default is 10. Remote media localization validates the original URL and every redirect target to reduce SSRF risk.

## Docker frontend assets

The Dockerfile copies the `app/` directory, so Studio and related pages are available in container deployments.
