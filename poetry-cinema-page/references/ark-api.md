# Image provider reference

`scripts/ark_image.py` can generate images through **two providers side by side**:

| Provider key | Kind | What it is |
| --- | --- | --- |
| `ark` | `ark` | Volcengine Ark (火山引擎方舟) Doubao Seedream 5.0 |
| `gpt-image` | `openai-images` | GPT-Image gateway (third-party, OpenAI-compatible, 咕皮生图) |

Both are configured in the same file, `config/ark.config.json`, and **the tier is the only thing that selects a provider**: `pro` / `lite` run on Ark, `gpt-2` / `gpt-2.5` on the gateway. A single poem may therefore mix them — an Ark hero can be the reference image a gateway beat continues from — and the reference chain survives the provider boundary.

**Verification scope.** Ark facts below — its endpoint and auth scheme, both model ids, the six request fields, the size limits, the response schema, the error schema, and both image-to-image input forms — were verified against the live Ark API. Gateway facts — both endpoints, the mandatory browser User-Agent, the multipart edits path, the silently ignored `image` field on generations, the `response_format` restriction, the size behaviour, the reference downscale, the failure modes and the error shape — were verified against the live gateway on the same machine. The gateway is third-party, and its model ids are **not** confirmed by the free connectivity probe. The mixed-provider numbers at the end of this document come from one real run that used both providers for the same poem. Items marked **(local)** describe the bundled CLI or `config/ark.config.json`; they are not part of any HTTP contract.

## Providers

| Provider key | Kind | Purpose | API key env var | Local key file | Endpoint | Native output | Can the free `probe` prove the model id? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ark` | `ark` | Volcengine Ark (火山引擎方舟) Doubao Seedream 5.0 | `ARK_API_KEY` | `config/ark.local.json` (git-ignored) | `POST https://ark.cn-beijing.volces.com/api/plan/v3/images/generations` | jpeg | yes — Ark validates `size` and resolves the model too |
| `gpt-image` | `openai-images` | GPT-Image gateway (third-party, OpenAI-compatible, 咕皮生图) | `GPT_IMAGE_API_KEY` | `config/gpt-image.local.json` (git-ignored) | `POST https://image.mlgb7.com/v1/images/generations` (text-to-image) and `POST https://image.mlgb7.com/v1/images/edits` (image-to-image) | png | no — the gateway validates the request body before the model, so only `--live` proves a model id |

Neither provider is billed by the free connectivity check; see [CLI](#cli).

## Tiers and provider selection

`models` maps a tier name to a `{provider, id}` pair:

| Tier | Provider | Model id | Use for |
| --- | --- | --- | --- |
| `pro` | `ark` | `doubao-seedream-5.0-pro` | hero, beat — highest quality; the Ark default tier |
| `lite` | `ark` | `doubao-seedream-5.0-lite` | draft, repair — cheaper and faster |
| `gpt-2` | `gpt-image` | `gpt-image-2` | alternative hero / beats on the gateway |
| `gpt-2.5` | `gpt-image` | `gpt-image-2.5` | alternative hero / beats on the gateway |

Ways to pick one **(local)**:

| Where | What it does |
| --- | --- |
| `image.provider` in the config | Sets the default provider — the one used by any tier that does not name its own. |
| `--tier NAME` | `pro`, `lite`, `gpt-2`, or `gpt-2.5`. |
| `--model NAME` | A raw model id, or a configured tier name; a tier name brings its own provider with it. |
| `--provider NAME` | Forces a provider by name for this call. `t2i`, `i2i` and `batch` honour it, and a batch entry's own `"provider"` wins over it. `probe` does not take it — probe through `--tier` instead, or let the tier→provider mapping in `models` decide. |
| `"provider": "gpt-image"` inside a batch-plan entry | Per-image override, so one plan can mix providers. |
| bare model-id string for a tier, e.g. `"pro": "doubao-seedream-5.0-pro"` | Legacy shape: the tier keeps working and uses the default provider. |

A config written entirely in the **old single-provider shape** — a top-level `api` block plus a top-level `limits`, with no `image` block — is still accepted and read as one provider named after `api.kind` (default `ark`), with `api.images_path` becoming its `generations_path`. Nothing has to be migrated to keep working; the `image.providers` shape is only needed once you want a second provider. See [Configuration](#configuration).

## Volcengine Ark (Doubao Seedream)

Provider key `ark`, kind `ark`.

### Endpoint and authentication

- Endpoint: `POST https://ark.cn-beijing.volces.com/api/plan/v3/images/generations`
- Auth: `Authorization: Bearer <ARK_API_KEY>`
- Body: JSON.

```bash
curl -sS https://ark.cn-beijing.volces.com/api/plan/v3/images/generations \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "model": "doubao-seedream-5.0-pro",
        "prompt": "A 16:9 wide horizontal cinematic still ... no text, calligraphy, seals, signatures, watermarks, logos, or modern objects anywhere in the image.",
        "size": "2560x1440",
        "response_format": "url",
        "watermark": false
      }'
```

Never write a real key into a tracked file, a prompt, a manifest, an issue, or a commit. See [Configuration](#configuration) for the resolution order.

### Models

| Tier | Model id | Use for | Notes |
| --- | --- | --- | --- |
| pro | `doubao-seedream-5.0-pro` | hero, beat | Highest quality. Default tier. Tolerates sizes below the lite minimum, but this skill does not use that. |
| lite | `doubao-seedream-5.0-lite` | draft, repair | Cheaper and faster. Strict minimum area of 3,686,400 px. |

The response echoes a normalized model id with dots replaced by dashes — a `doubao-seedream-5.0-pro` request comes back as `"model": "doubao-seedream-5-0-pro"`. Match on the request id, not the echoed one.

Role routing **(local)**, from `routing` in the config file: `hero → pro`, `beat → pro`, `draft → lite`, `repair → lite`. Routing names tiers, not providers, so re-pointing `routing` at `gpt-2` moves that role to the gateway.

### Request fields

All six are verified as supported. `model`, `prompt`, and `size` are present in every request this skill sends.

| Field | Type | Value used here | Notes |
| --- | --- | --- | --- |
| `model` | string | `doubao-seedream-5.0-pro` or `doubao-seedream-5.0-lite` | Chosen by role via the config routing, or overridden with `--tier` / `--model`. |
| `prompt` | string | one natural-language paragraph | There is **no** negative-prompt field. Style flags such as `--ar 16:9` are not parameters. Put the frame, the composition and the exclusions in prose. |
| `size` | string | `2560x1440` | Explicit `WIDTHxHEIGHT`. Never a shorthand. See [Size rules](#size-rules). |
| `response_format` | string | `"url"` | Verified value. The image comes back as a downloadable URL in `data[].url`. |
| `watermark` | boolean | `false` | Verified value. Keep it `false`; typography is added in HTML. |
| `image` | array of strings | omitted for text-to-image; the reference chain otherwise | Image-to-image input. Each element is a public image URL or a `data:image/jpeg;base64,...` URI. See [Image-to-image](#image-to-image). |

### Size rules

| Rule | Value | Evidence |
| --- | --- | --- |
| Accepted form | `WIDTHxHEIGHT` string | `"2560x1440"` |
| Shorthand | do not use | `"2K"` returned **1664x2496** (portrait) for a landscape prompt — the ratio of a shorthand is not guaranteed. |
| Minimum area, `lite` | 3,686,400 px | `2048x1152` rejected with `InvalidParameter`: `image size must be at least 3686400 pixels`. |
| Minimum area, `pro` | below the lite minimum | `pro` accepts smaller sizes, but this skill uses one size for both tiers so results stay comparable. |
| Maximum area | 4,624,220 px | `8192x4608` was rejected. |
| Recommended 16:9 | **`2560x1440`** = 3,686,400 px exactly | The only 16:9 value that both `pro` and `lite` accept. Use it for every page image. |

Presets **(local)** in `size_presets`, usable as `--size <preset>`:

| Preset | Value | Area |
| --- | --- | --- |
| `web_16_9` | `2560x1440` | 3,686,400 px — the skill default, and the only one both Ark tiers accept |
| `web_16_9_1080` | `1920x1080` | 2,073,600 px — below the Ark band; a 16:9 gateway alternative |
| `square` | `1024x1024` | 1,048,576 px — below the Ark band; usable on the gateway |
| `portrait` | `1024x1536` | 1,572,864 px — below the Ark band; usable on the gateway |
| `auto` | `auto` | gateway-only, and only passed through when that provider sets `limits.allow_auto` |

Verify the delivered frame from the response: `data[].size` reports what was actually produced, so a successful call is not proof that you got 16:9.

### Response schema

```json
{
  "model": "doubao-seedream-5-0-pro",
  "created": 1789996132,
  "data": [
    {
      "url": "https://...",
      "size": "2048x1152",
      "output_format": "jpeg"
    }
  ],
  "usage": {
    "input_images": 0,
    "generated_images": 1,
    "output_tokens": 9216,
    "total_tokens": 9216
  }
}
```

- `data[].url`: the generated image, downloadable over plain HTTPS.
- `data[].output_format`: `jpeg` in every verified response.
- `data[].size`: the real pixel dimensions. Check this field.
- `usage.input_images`: how many references were passed in `image` (0 for text-to-image).
- `usage.generated_images`, `usage.output_tokens`, `usage.total_tokens`: accounting, useful for cost tracking.

Delivered files arrive as **JPEG, roughly 250–500 KB at 2560x1440** (measured: 340–487 KB from `pro`, 253–390 KB from `lite`) — already inside the web delivery budget, so no re-encode step is required. `output.keep_api_urls` **(local)** decides whether the original API URLs are retained in the manifest.

When `data[].output_format` is missing, the CLI infers the format from the result URL and rewrites a mismatched output extension, printing a `note:` when it does **(local)** — a `.png` result is never written under a `.jpg` name.

**Measured latency at 2560x1440 (per image, single run):** `pro` ≈ 55–95 s (text-to-image and image-to-image alike), `lite` ≈ 22–35 s. Budget roughly a minute per `pro` image when planning a six-to-eight image set, and prefer `lite` for drafts and repairs where the extra fidelity of `pro` is not yet needed. The gateway is slower and less predictable; see [GPT-Image gateway](#gpt-image-gateway).

### Error schema

Validation failure, HTTP 400:

```json
{"error": {"code": "InvalidParameter", "message": "...", "param": "size", "type": "BadRequest"}}
```

Unavailable model, HTTP 404:

```json
{"error": {"code": "UnsupportedModel", "message": "..."}}
```

| Code | HTTP | Meaning | Correct response |
| --- | --- | --- | --- |
| `InvalidParameter` | 400 | The request was rejected at validation. `param` names the offending field — most often `size`. | Fix the named field and resend. Typical causes: an area outside 3,686,400–4,624,220 px, a shorthand size, or a model/size combination `lite` refuses. A retry with the same body will fail the same way. |
| `UnsupportedModel` | 404 | The model id is not available to this key, this endpoint, or this region. | Check `models.pro` / `models.lite` and the Ark provider's `base_url`, then run `probe`. Do not retry unchanged. |

The provider's `max_retries` and `retry_backoff_seconds` **(local)** bound how often the CLI repeats a failed request. Neither error above becomes valid on a retry, so treat a 400 or 404 as a request bug to fix, not as a transient failure to wait out.

### Image-to-image

Pass `image` as an **array** of strings. Each element is a public image URL or a `data:image/jpeg;base64,....` URI. Omitting `image` makes the call text-to-image. Both forms were verified working, including several references in one call.

Public URL:

```json
{
  "model": "doubao-seedream-5.0-pro",
  "prompt": "Continue the world of the reference image exactly ...",
  "size": "2560x1440",
  "response_format": "url",
  "watermark": false,
  "image": ["https://example.com/hero.jpg"]
}
```

Local file as a base64 data URI:

```json
{
  "image": ["data:image/jpeg;base64,<base64-encoded hero JPEG>"]
}
```

`scripts/ark_image.py` encodes whatever you pass to `--ref` automatically **(local)**: a local path becomes a data URI, an `http(s)` URL is forwarded as is. There is no separate upload step.

Several references in one call — the hero for the world plus a character image for a recurring figure:

```json
{
  "image": [
    "data:image/jpeg;base64,<hero>",
    "data:image/jpeg;base64,<recurring character>"
  ]
}
```

Name in the prompt which reference owns what, since the API receives an ordered array with no roles attached.

Inside a batch plan **(local)**, `"ref": ["hero"]` is a friendlier form: it resolves to the already-generated `hero` image inside `out_dir`, so the hero must appear earlier in the plan than any beat that references it.

Ark takes at most `limits.max_reference_images` references in one call (10 in the shipped config); the gateway takes 4. A cross-provider reference is fine — the CLI converts the parent provider's file into whatever the target provider needs.

## GPT-Image gateway

Provider key `gpt-image`, kind `openai-images`: a third-party OpenAI-compatible gateway at `https://image.mlgb7.com/v1` (咕皮生图). "OpenAI-compatible" describes the request shape only — this is not the official OpenAI API. Everything in this section was verified against the live gateway.

### Two endpoints, two jobs

| Endpoint | Use for | Body |
| --- | --- | --- |
| `POST {base}/images/generations` | **text-to-image only** | JSON: `{model, prompt, n, size, response_format:"url"}` |
| `POST {base}/images/edits` | **image-to-image** — any call that carries a reference | `multipart/form-data`, the reference file in a part literally named `image` |

**The `image` field is silently ignored on `/images/generations`.** Passing `image`, `image_url`, or `images` there is not an error: the request succeeds with 200 and produces a fresh text-to-image result. That quietly turns an image-to-image call into a new picture, which breaks the hero-as-reference consistency design — every beat still looks plausible on its own while the set drifts apart. Never move a reference call onto `generations`, and never "simplify" the edits call away; the gateway's own frontend bundle documents the same form (`/v1/images/edits` with `-F "image=@./reference.png"`).

Text-to-image, verified:

```bash
curl -sS https://image.mlgb7.com/v1/images/generations \
  -H "Authorization: Bearer $GPT_IMAGE_API_KEY" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-image-2", "prompt": "...", "n": 1, "size": "2560x1440", "response_format": "url"}'
```

Response:

```json
{
  "created": 1789996132,
  "data": [
    {"url": "https://...", "revised_prompt": "..."}
  ]
}
```

Image-to-image, verified — multipart, file field named `image`:

```bash
curl -sS https://image.mlgb7.com/v1/images/edits \
  -H "Authorization: Bearer $GPT_IMAGE_API_KEY" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36" \
  -F "model=gpt-image-2.5" \
  -F "prompt=..." \
  -F "n=1" \
  -F "size=1792x1024" \
  -F "response_format=url" \
  -F "image=@./hero.jpg"
```

The bundled CLI picks the endpoint by itself **(local)**: any call with a reference goes to `edits_path` as multipart, anything else goes to `generations_path` as JSON. `--dry-run` shows which one it chose and lists the files it would upload.

### A browser User-Agent is mandatory

The gateway sits behind Cloudflare. The default urllib User-Agent is answered with **`error code: 1010`** before the request ever reaches the API, so a browser-like UA is not cosmetic — without it nothing works. The client sends the provider's `user_agent` (Chrome's UA in the shipped config) plus `Accept`, `Accept-Language`, `Origin`, and `Referer` headers. Keep `user_agent` in the provider block.

### `response_format`

Only `url` is accepted. `b64_json` is refused:

```
400 bad_request: 站点用户 API 目前仅支持 response_format=url
```

### Sizes

**Nothing is validated.** `2560x1440`, `1792x1024`, `1024x1024`, `1024x1536` and `auto` all work — and so do nonsense values such as `1x1` and `abc`, which return 200. Size therefore cannot act as a safety net here the way it does on Ark; this skill enforces the configured `limits.min_edge_px` / `limits.max_edge_px` band (256 / 8192 in the shipped config) in the CLI before spending a call **(local)**. The literal `auto` is only forwarded when the provider sets `limits.allow_auto`, which the shipped config does not do, so pass an explicit `WIDTHxHEIGHT` unless you deliberately opt in.

**Aspect ratio is honoured; resolution is not.** The gateway snaps the output to its own bucket of roughly 1670 px on the long edge, so the pixel count you ask for is not the pixel count you get. Measured against `gpt-image-2` and confirmed with `ffprobe`:

| requested | returned | ratio | 16:9? |
| --- | --- | --- | --- |
| `2560x1440` | `1672x941` | 1.777 | yes |
| `1920x1080` | `1672x941` | 1.777 | yes |
| `1536x864` | `1672x941` | 1.777 | yes |
| `1792x1024` | `1659x948` | 1.750 | no — that request is 7:4 |
| `1024x1024` | `1254x1254` | 1.000 | no |
| `auto` | `1448x1086` | 1.333 | no |

Two consequences **(local)**: request a genuine 16:9 size when the page stage needs one, because the gateway preserves whatever ratio you ask for — including a wrong one; and do not expect gateway output to be as sharp as Ark's `2560x1440`, since you receive about 1672x941. The manifest records the *requested* size, because the gateway echoes only `url` and `revised_prompt` and never reports the dimensions it produced.

The gateway returns **PNG**. The CLI infers the format from the result URL when the API omits `output_format` and rewrites the extension, printing `note: the API returns png, so 'hero.jpg' was written as 'hero.png'` **(local)**. The manifest records the path that was actually written.
### Reference uploads are downscaled before sending

Large uploads fail: a **366 KB** uploaded reference came back as `RemoteDisconnected`, while the same image at **22 KB** succeeded. The client therefore resizes every reference to `reference_max_edge` (1536 px) before an upload **(local)**. Measured: a 2061 KB / 1672x940 reference became 224 KB, and a 443 KB / 2560x1440 one became 231 KB. References that came from Ark are downscaled the same way when they are fed into a gateway call, so a cross-provider reference works at full size on the Ark side and arrives compressed on the gateway side. The resize is best-effort: if Pillow is unavailable, or the resize fails, the original file is uploaded as-is instead of blocking the run.

### Flakiness and retries

The gateway is unstable under load. Observed in live runs: `RemoteDisconnected`, `SSL: UNEXPECTED_EOF_WHILE_READING`, and Cloudflare `502` / `520` / `522` responses. A full 8-image set generated on `gpt-image-2.5` needed **16 retries** across the run, and two of the eight images exhausted a four-attempt budget and had to be re-run — which is why its `max_retries` is **5** (against Ark's 2). Retries apply to the 5xx family, 408/409/425/429, and connection-level failures; the pause grows with each attempt. Re-running the same `batch` plan is the supported recovery: finished images are skipped and only the missing ones are attempted again.

A `504` can also mean the gateway accepted the job and lost track of it: it exposes `/api/image-tasks?ids=<task_id>` on the gateway host for polling such a task. The bundled CLI does not poll it — treat it as a manual rescue valve, not part of the normal flow.

### Error shape
```json
{"error": {"message": "...", "type": "...", "param": "...", "code": "..."}}
```

Observed examples: `401 invalid_api_key` for a rejected key, and `422 bad_request` for body validation. The CLI maps 401/403 to a key hint naming that provider's environment variable, and the 502/503/504/520/522 family to an overload hint suggesting higher retry settings.

## Configuration

`skills/poetry-cinema-page/config/ark.config.json` is the single source of truth for both providers — endpoints, models, routing, sizes, timeouts. Change behaviour there, not in the CLI.

`image`:

| Key | Value | Meaning |
| --- | --- | --- |
| `image.provider` | `ark` | Default provider name. Used by any tier that does not name its own provider. Must be one of the keys in `image.providers`. |
| `image.providers.<name>` | object | One entry per provider. `<name>` is the key you pass to `--provider` and write into `models.<tier>.provider`. |

Per-provider keys:

| Key | `ark` | `gpt-image` | Meaning |
| --- | --- | --- | --- |
| `kind` | `ark` | `openai-images` | Dialect: decides JSON vs multipart, how references travel, and whether the free probe can vouch for the model id. |
| `label` | … | … | Human-readable name used in progress lines and error messages. |
| `base_url` | `https://ark.cn-beijing.volces.com/api/plan/v3` | `https://image.mlgb7.com/v1` | API root. Absolute, no trailing slash. |
| `generations_path` | `/images/generations` | `/images/generations` | Appended to `base_url` for text-to-image. |
| `edits_path` | — | `/images/edits` | Appended to `base_url` for multipart image-to-image. |
| `api_key` | `""` | `""` | Last-resort inline key. This file is committed — leave it empty. |
| `api_key_env` | `ARK_API_KEY` | `GPT_IMAGE_API_KEY` | Name of the environment variable that takes priority. |
| `local_override` | `config/ark.local.json` | `config/gpt-image.local.json` | Git-ignored local key file, relative to the skill root. |
| `timeout_seconds` | `300` | `600` | Per-request timeout. Generous on both sides: `pro` calls are slow, and the gateway is slower. |
| `max_retries` | `2` | `5` | How often a failed request may be repeated. |
| `retry_backoff_seconds` | `6` | `5` | Pause between attempts; it grows with each retry. |
| `reference_transport` | `inline` | `multipart` | How references travel: Ark takes URLs / base64 data URIs inside the JSON body, the gateway takes uploaded files. |
| `response_format` | — | `url` | The gateway accepts `url` only. |
| `reference_max_edge` | — | `1536` | Longest edge a reference is resized to before an upload **(local)**. |
| `user_agent` | — | Chrome UA | Browser-like User-Agent; mandatory behind Cloudflare. |
| `limits` | `min_area_px 3686400`, `max_area_px 4624220`, `max_reference_images 10` | `min_edge_px 256`, `max_edge_px 8192`, `max_reference_images 4` | The band this skill enforces per provider before spending a call. Ark's is an area band, the gateway's is an edge band. |

`models`: `pro → {provider: ark, id: doubao-seedream-5.0-pro}`, `lite → {provider: ark, id: doubao-seedream-5.0-lite}`, `gpt-2 → {provider: gpt-image, id: gpt-image-2}`, `gpt-2.5 → {provider: gpt-image, id: gpt-image-2.5}`. A tier may also be written as a bare model-id string (the legacy shape), which then uses the default provider.

`routing`: which tier each role uses — `hero → pro`, `beat → pro`, `draft → lite`, `repair → lite`.

`defaults`: `role → beat`, `tier → pro`, `size → 2560x1440`, `response_format → url`, `watermark → false`. These apply to any call that does not specify the value.

`size_presets`: `web_16_9 → 2560x1440`, `web_16_9_1080 → 1920x1080`, `square → 1024x1024`, `portrait → 1024x1536`, `auto → auto`. Referenced by name through `--size`. Only `web_16_9` sits inside Ark's area band; the others are gateway sizes. There is deliberately no 7:4 or 4:3 preset, because the page stage is 16:9 and the gateway preserves whatever ratio you request.

`output`: `master_dir → public/generated` (where poem image sets live), `manifest_name → prompts.json`, `contact_sheet_name → contact-sheet.html`, `keep_api_urls → true` (retain the API URLs in the manifest).

The shipped file also carries a few auxiliary keys — `_readme` notes, `defaults.image_format`, `output.contact_sheet_columns`, `limits.size_notes` — which annotate the values above and control output formatting.

### Key resolution order

Each provider resolves **its own** key, independently — two providers in one run never share a credential:

1. **that provider's environment variable** — `ARK_API_KEY` for `ark`, `GPT_IMAGE_API_KEY` for `gpt-image`; wins whenever it is set;
2. **that provider's local override file** — `config/ark.local.json` or `config/gpt-image.local.json`, at the path in the provider's `local_override`. For `ark`:

   ```json
   { "api_key": "ark-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" }
   ```

   For `gpt-image`:

   ```json
   { "api_key": "lupi_xxxxxxxxxxxxxxxxxxxx" }
   ```

3. **`api_key` inside that provider's block in `ark.config.json`** — fallback only, and empty by default.

`ark.config.json` is committed to a public repository. Never put a real key in it; keep keys in the environment variables or in the local files, which `.gitignore` already excludes. A missing key is reported per provider, naming the exact environment variable and file path to create.

## CLI

```bash
python scripts/ark_image.py probe
python scripts/ark_image.py t2i   --prompt "<text>" --out <file>
python scripts/ark_image.py i2i   --prompt "<text>" --ref <file-or-url> [--ref <file-or-url> ...] --out <file>
python scripts/ark_image.py batch --plan <plan.json>
```

Run these from the skill root. `probe` resolves each provider's key, reports every configured provider (name, kind, endpoint, masked key and where it came from), and then checks every configured model by sending one request that is rejected on purpose by body validation — no image is generated and nothing is billed. Run it before every generation session.

That free check is not equally strong on both providers:

- **Ark**: the canary is `size: "1x1"`, which Ark validates strictly and which also proves the model id, because Ark resolves the model before validating the body.
- **GPT-Image gateway**: the canary is `n: 0`, because the gateway validates the request body first and accepts nonsense sizes. A green result therefore means *endpoint reachable, key accepted* — the CLI prints `model id NOT verified; use --live for that` for gateway models. Only `--live` proves a gateway model id by actually generating one image per tier (which costs time and quota, and runs at the configured default size).

Common flags:

| Flag | Value | Effect |
| --- | --- | --- |
| `--config PATH` | config file path | Use a configuration file other than `config/ark.config.json`. |
| `--tier pro\|lite\|gpt-2\|gpt-2.5` | tier | Pick the tier explicitly, overriding the role routing. |
| `--provider NAME` | provider key | Force a provider by name for this call. Honoured by `t2i`, `i2i` and `batch`; a batch entry's own `provider` wins. Not used by `probe`. |
| `--model NAME` | model id or tier name | Pick the model explicitly; a configured tier name also selects that tier's provider. |
| `--size WxH\|preset-name` | size or preset | Default `2560x1440`. Pass an explicit `WxH`, or a `size_presets` name. |
| `--role hero\|beat\|draft\|repair` | role | Selects the tier through `routing`. |
| `--n N` | count | Repeat the call N times. |
| `--out-dir DIR` | directory | Directory used to resolve sibling reference names. |
| `--name NAME` | asset name | Label used for the asset in the manifest. |
| `--dry-run` | — | Print the resolved request without contacting the API, and without needing an API key. Honoured by `probe`, `t2i`, `i2i` and `batch`. |
| `--json` | — | Emit one JSON document on stdout; progress lines move to stderr so the output stays pipeable. For `probe` the document is its report; for the other subcommands it is the list of records. |
| `--no-manifest` | — | Skip writing `prompts.json` and `contact-sheet.html`. |
| `--force` | — | `batch` only. Regenerate entries whose file already exists; the default skips them and keeps them in the manifest. |
| `--live` | — | `probe` only. Generate one real image per model as well, which proves gateway model ids. |

Batch plan **(local)** — one poem, one command. Each entry may carry `role`, `tier`, `model`, `provider`, `size` and `ref`, so provider switching happens per image:

```json
{
  "out_dir": "public/generated/<poem-slug>",
  "images": [
    {"name": "hero",    "role": "hero", "prompt": "..."},
    {"name": "scene-1", "role": "beat", "ref": ["hero"], "prompt": "..."},
    {"name": "scene-2", "role": "beat", "ref": ["hero"], "tier": "gpt-2", "provider": "gpt-image", "prompt": "..."}
  ]
}
```

`"ref": ["hero"]` means "use the already-generated `hero` image inside `out_dir` as the image-to-image reference", so the hero is listed first and beats follow in poem order. `batch` also writes `prompts.json` — a manifest recording every request and response — and `contact-sheet.html` for the mandatory inspection step, both into `out_dir`.

## Worked example: one poem, two providers

A real run on the author's machine, mixing both providers inside a single image set. The hero came from Ark; the next beat ran on the gateway and used that Ark hero as its reference. Everything below is measured, not estimated.

| Step | Tier · provider | Model id | Size | Reference | Result | Time |
| --- | --- | --- | --- | --- | --- | --- |
| hero, text-to-image | `pro` · `ark` | `doubao-seedream-5.0-pro` | 2560x1440 | — | 444 KB, `.jpg` | 39.0 s |
| beat, image-to-image | `gpt-2` · `gpt-image` (multipart edits) | `gpt-image-2` | 1792x1024 | the Ark hero above | 2129 KB, `.png` | 53.6 s |
| standalone text-to-image | `gpt-2` · `gpt-image` | `gpt-image-2` | 2560x1440 | — | 2062 KB, `.png` | 266.2 s after 3 retries |
| standalone reference-to-image | `gpt-2.5` · `gpt-image` | `gpt-image-2.5` | 1792x1024 | 2061 KB reference → 224 KB after resize | 2463 KB, `.png` | 62.4 s |

### A full 8-image set on the gateway

The same eight prompts were then rendered entirely on `gpt-2.5` (identical wording, so the two sets are directly comparable). Measured end to end:

| | Ark set (`doubao-seedream-5.0-pro`) | gateway set (`gpt-image-2.5`) |
| --- | --- | --- |
| images produced | 8 / 8 | 8 / 8, but two needed a second `batch` run |
| actual frame | 2560x1440 JPEG | 1672x940 / 1672x941 PNG |
| per-image bytes | 286–893 KB | 1954–2401 KB |
| per-image time | 70–111 s | 125–274 s |
| wall clock | ~12 min | ~28 min, then ~4.5 min to fill the two gaps |
| retry lines | 0 | 16, plus 3 more during the top-up |
| reference chain | intact (inline) | intact (multipart, verified per entry) |

Two lessons worth carrying into any gateway run: budget roughly **two to three times** Ark's wall clock, and expect to run the plan **twice** — the second pass skips what already exists and only pays for the gaps.

What the run shows:

- **The reference chain crosses providers.** The gateway beat inherited the Ark hero's world through `/images/edits`, which is the whole point of the tier-based provider selection: hero and beats do not have to come from the same service.
- **Expect the gateway to be slow and to need retries.** One standalone call took 266.2 s and three retries before it succeeded, while the same route with a reference answered in under 65 s.
- **Expect PNG where you asked for `.jpg`.** The gateway returns PNG, so the CLI wrote `scene-1.png` next to a `--out` that ended in `.jpg` and printed a `note:` about it. Read the manifest, not the requested filename.
- **Budget the bandwidth.** Ark output sits at roughly 250–500 KB per image, gateway output at roughly 2 MB per image. Both are usable on the web, but they are not the same budget.

For Ark-only sizing rules and error codes, see the Ark section above; for the gateway's traps, see [GPT-Image gateway](#gpt-image-gateway). Visual-direction rules that apply to both providers live in [image-direction.md](image-direction.md).
