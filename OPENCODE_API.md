# OpenCode API — How to Use It Without Getting Blocked

> **Last updated:** 2026-09-11
>
> This document describes the undocumented OpenCode API (`/zen/v1/chat/completions`), the required headers to avoid 400 errors, and the patterns that keep you from getting rate-limited or blocked.

---

## Table of Contents

1. [Endpoint](#1-endpoint)
2. [Required Headers](#2-required-headers)
3. [Payload](#3-payload)
4. [Error Codes and What They Mean](#4-error-codes-and-what-they-mean)
5. [Rate Limiting and Retries](#5-rate-limiting-and-retries)
6. [Working Examples](#6-working-examples)
7. [What Will Get You Blocked](#7-what-will-get-you-blocked)
8. [Known Limitations](#8-known-limitations)
9. [Do's and Don'ts](#9-dos-and-donts)

---

## 1. Endpoint

```
POST https://opencode.ai/zen/v1/chat/completions
```

This is **not** a standard OpenAI-compatible endpoint. It is proxied through OpenCode's infrastructure and requires additional headers.

---

## 2. Required Headers

All of the following headers are **mandatory**. Omitting any one of them will result in a **400 Bad Request**.

```python
headers = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
    "x-opencode-client": "opencode",
    "x-opencode-session": "ses_<24-char-random-hex>",
    "x-opencode-request": "req_<24-char-random-hex>",
    "User-Agent": "opencode/1.18.15",
}
```

### Header Details

| Header | Value | Notes |
|--------|-------|-------|
| `Content-Type` | `application/json` | Standard JSON payload |
| `Accept` | `text/event-stream` | Required for streaming responses |
| `x-opencode-client` | `opencode` | Client identifier — must be exactly `opencode` |
| `x-opencode-session` | `ses_<24-char-hex>` | Unique per session/connection. Format: `ses_` + 24-char hex |
| `x-opencode-request` | `req_<24-char-hex>` | Unique per API call. Format: `req_` + 24-char hex |
| `User-Agent` | `opencode/1.18.15` | Versioned client identifier |

### Generating Session and Request IDs

Both IDs **must be regenerated for every request**. Reusing them may cause 403 or 429 errors.

**Python:**
```python
import secrets

session_id = "ses_" + secrets.token_hex(12)  # 24 hex chars
request_id  = "req_" + secrets.token_hex(12)  # 24 hex chars
```

**Bash:**
```bash
SESSION_ID="ses_$(openssl rand -hex 12)"
REQUEST_ID="req_$(openssl rand -hex 12)"
```

---

## 3. Payload

```json
{
  "model": "big-pickle",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.7,
  "stream": true
}
```

### Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `model` | string | Yes | See [available models](#available-models) |
| `messages` | array | Yes | Standard OpenAI message format |
| `temperature` | float | No | Controls randomness (0.0–2.0). Default varies by model |
| `stream` | bool | No | **Recommended: `true`**. Non-streaming may return 503 |

### Available Models

| Model | Description |
|-------|-------------|
| `big-pickle` | Primary model |
| `mimo-v2.5-free` | Free-tier model |

> **Important:** `stream: true` is strongly recommended. The API may return **503** if streaming is not enabled.

---

## 4. Error Codes and What They Mean

| Code | Meaning | Fix |
|------|---------|-----|
| **400** Bad Request | Missing required headers (`x-opencode-client`, `x-opencode-session`, etc.) | Add all required headers |
| **403** Forbidden | Invalid or reused session/request IDs | Regenerate IDs per request |
| **429** Too Many Requests | Rate limited | Exponential backoff, respect `Retry-After` header |
| **503** Service Unavailable | Server overloaded **or** `stream: false` not supported | Enable `stream: true`, retry with backoff |

---

## 5. Rate Limiting and Retries

### Strategy

```python
import asyncio
import httpx

async def call_with_retry(func, max_retries=3, base_delay=2.0):
    for attempt in range(max_retries):
        try:
            return await func()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                if retry_after:
                    delay = float(retry_after)
                else:
                    delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
            elif e.response.status_code == 503:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
            else:
                raise
    raise Exception("Max retries exceeded")
```

### Rules

- **Exponential backoff on 429:** `delay = base_delay * (2 ** attempt)`
- **Respect `Retry-After` header** if present — use its value instead of backoff calculation
- **Max 3 retries** recommended
- **On 503:** retry with backoff (server may be temporarily overloaded)

---

## 6. Working Examples

### Python (httpx)

```python
import secrets
import httpx

async def call_opencode_api(
    system_prompt: str,
    user_prompt: str,
    model: str = "big-pickle",
) -> str:
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "x-opencode-client": "opencode",
        "x-opencode-session": "ses_" + secrets.token_hex(12),
        "x-opencode-request": "req_" + secrets.token_hex(12),
        "User-Agent": "opencode/1.18.15",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.post(
            "https://opencode.ai/zen/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
```

### curl

```bash
curl -N 'https://opencode.ai/zen/v1/chat/completions' \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -H 'x-opencode-client: opencode' \
  -H "x-opencode-session: ses_$(openssl rand -hex 12)" \
  -H "x-opencode-request: req_$(openssl rand -hex 12)" \
  -H 'User-Agent: opencode/1.18.15' \
  --data-raw '{
    "model": "mimo-v2.5-free",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'
```

---

## 7. What Will Get You Blocked

| Action | Result |
|--------|--------|
| Calling without `x-opencode-client` header | **400** Bad Request |
| Reusing session/request IDs across calls | **403** Forbidden / **429** Too Many Requests |
| Too many requests without backoff | **429** Too Many Requests |
| Not enabling `stream: true` | **503** Service Unavailable |
| Using an invalid model name | **400** Bad Request |

---

## 8. Known Limitations

- **No official API key mechanism** — authentication is header-based (client identification), not token-based
- **Proxied endpoint** — the API goes through `opencode.ai/zen/v1/`, not a standard OpenAI-compatible server
- **Rate limits are undocumented** — observe `429` responses to discover limits
- **Streaming may be required** — non-streaming (`stream: false`) may not work reliably and can return 503
- **Model availability may change** — the list above reflects observed models, not guaranteed contracts

---

## 9. Do's and Don'ts

### ✅ Do

- **Regenerate session and request IDs** for every API call
- **Enable streaming** (`stream: true`) — it's more reliable
- **Implement exponential backoff** on 429 and 503 errors
- **Set a generous timeout** (600s+) — streaming responses can be slow
- **Respect the `Retry-After` header** when present
- **Check the model name** is valid before sending

### ❌ Don't

- **Don't reuse session/request IDs** — this triggers 403/429
- **Don't call without all required headers** — you'll get 400
- **Don't retry immediately** on 429 — back off exponentially
- **Don't use `stream: false`** — you'll likely get 503
- **Don't assume rate limits** — they're undocumented; observe and adapt
- **Don't hardcode session IDs** — they must be unique per session

---

*This documentation is based on observed API behavior from real bug investigations and fixes. The OpenCode API is not officially documented — use at your own discretion.*
