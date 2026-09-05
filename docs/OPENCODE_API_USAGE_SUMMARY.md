# OpenCode Zen API — Usage Summary

## Endpoint

```
POST https://opencode.ai/zen/v1/chat/completions
```

## Headers

| Header | Value | Required? |
|--------|-------|-----------|
| `Content-Type` | `application/json` | ✅ Yes — body is JSON |
| `User-Agent` | `opencode/1.18.15` | ✅ Yes — identifies the client; likely required for access |

No `Authorization` header needed. No API key.

## Example (Python + httpx)

```python
import httpx

async def generate_quiz(topic: str) -> str:
    resp = await httpx.AsyncClient(timeout=600).post(
        "https://opencode.ai/zen/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "opencode/1.18.15",
        },
        json={
            "model": "big-pickle",
            "messages": [
                {"role": "system", "content": "You are a quiz generator."},
                {"role": "user", "content": f"Create quizzes about: {topic}"},
            ],
            "temperature": 0.7,
        },
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
```

Response follows OpenAI format: `choices[0].message.content` contains the answer string.

Source: `bot/services/ai_service.py` in [BotDeEncuestas](https://github.com/somesupercoder/BotDeEncuestas).
