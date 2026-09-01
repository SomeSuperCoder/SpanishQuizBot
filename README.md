<div align="center">

# 🤖 BotDeEncuestas

**AI-powered Telegram quiz generator for Spanish language learners**

Build, review, and publish Spanish quizzes to Telegram channels — fully automated, powered by AI.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![aiogram 3.x](https://img.shields.io/badge/aiogram-3.x-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://docs.aiogram.dev)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![uv](https://img.shields.io/badge/uv-managed-D4AA00?style=flat-square&logo=uv&logoColor=white)](https://docs.astral.sh/uv/)

---

</div>

## ✨ What It Does

BotDeEncuestas is a Telegram bot that lets you **auto-generate, auto-review, and publish Spanish language quizzes** — directly to Telegram channels. Forward a post from a Spanish channel, and the AI does the rest: detects the topic, picks the CEFR level, selects appropriate quiz categories, and generates a complete quiz ready for publication.

Designed for **Russian-speaking students** learning Spanish, with full support for multiple dialects and CEFR levels from A1 to C2.

---

## 🧩 Features

| | Feature | Description |
|---|---------|-------------|
| 🧠 | **AI-Powered Generation** | Quizzes generated via AI with configurable categories and difficulty |
| 🌐 | **Multi-Language Quizzes** | Spanish AND Russian question content — independent per language |
| 🔍 | **Smart Auto-Detection** | Forward a channel post → AI extracts topic, CEFR level, and dialect |
| 📝 | **4 Quiz Categories** | Fill blank · Meaning · Synonyms/Antonyms · Slang/Educado |
| 🗣️ | **Dialect Support** | Castellano 🇪🇸 · Mexicano 🇲🇽 · Argentino 🇦🇷 |
| ✅ | **Auto-Review** | AI self-reviews quizzes for correctness, no duplicates, proper categories |
| 📢 | **Channel Publishing** | Publish quizzes directly to any connected Telegram channel |
| ⏱️ | **Scheduled Publishing** | Gradual publication with configurable intervals between quizzes |
| 📦 | **Post Accumulation** | Forward multiple posts to build comprehensive weekly quizzes |
| 🔒 | **Access Control** | Username whitelist middleware — only authorized users interact with the bot |
| 🌍 | **Proxy Support** | Automatic SOCKS/HTTP proxy detection for regions where Telegram is blocked |

---

## 🏗️ Architecture

```
bot/
├── main.py              ← Entry point: bot init, proxy detection, polling
├── config.py            ← Pydantic settings (env vars + validation)
├── handlers/
│   ├── start.py         ← /start, /link, channel add/remove events
│   ├── survey.py        ← Full quiz creation flow (FSM, generation, review, publish)
│   └── callbacks.py     ← Callback query handlers
├── services/
│   └── ai_service.py    ← AI integration (generate, review, edit, auto-detect)
├── database/
│   ├── connection.py    ← SQLite async initialization
│   └── repository.py    ← UserRepository, BotConfigRepository, SurveyRepository
├── keyboards/
│   └── inline.py        ← Inline keyboards (categories, counters, levels, dialects)
├── middleware/
│   └── whitelist.py     ← Username whitelist access control
└── states/
    └── survey.py        ← FSM states for the survey creation flow
```

**Key design decisions:**
- **Async everything** — aiogram 3.x + aiosqlite + httpx, no blocking calls
- **FSM-driven flows** — state machines manage multi-step quiz creation
- **Repository pattern** — clean data access layer, easy to swap SQLite for Postgres
- **Middleware architecture** — whitelist checks happen at the middleware layer, not in handlers

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- A Telegram Bot Token ([@BotFather](https://t.me/BotFather))

### Install & Run

```bash
# Clone the repository
git clone https://github.com/somesupercoder/BotDeEncuestas.git
cd BotDeEncuestas

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your BOT_TOKEN and WHITELIST_USERNAMES

# Run the bot
uv run bot
```

That's it. The bot will detect proxy settings automatically if needed.

---

## ⚙️ Configuration

Create a `.env` file in the project root:

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `BOT_TOKEN` | `str` | ✅ | Telegram Bot API token from [@BotFather](https://t.me/BotFather) |
| `WHITELIST_USERNAMES` | `JSON array` | ✅ | List of allowed Telegram usernames, e.g. `["alice","bob"]` |
| `DATABASE_PATH` | `str` | ❌ | SQLite database path (default: `bot.db`) |
| `PROXY_URL` | `str` | ❌ | SOCKS/HTTP proxy URL for Telegram API access |

### Example `.env`

```env
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
WHITELIST_USERNAMES=["alice","bob","charlie"]
DATABASE_PATH=bot.db
PROXY_URL=http://127.0.0.1:10809
```

> **Proxy:** If you're in a region where Telegram is blocked, set `PROXY_URL`. The bot supports both HTTP and SOCKS5 proxies and will auto-detect from environment variables as well.

---

## 🔄 User Flow

```
┌─────────────────────────────────────────────────────┐
│  1. START                                            │
│  User sends /start → bot registers and shows menu    │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  2. CREATE QUIZ                                      │
│  Click "Crear encuesta" → choose mode:               │
│  • Manual topic input                                │
│  • Auto-detect from forwarded Spanish channel post   │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  3. CONFIGURE                                        │
│  • Select quiz categories (📝📖🔄🎭)                │
│  • Choose CEFR level (A1 → C2)                       │
│  • Pick dialect (🇪🇸 🇲🇽 🇦🇷)                         │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  4. GENERATE & REVIEW                                │
│  AI generates quizzes → auto-reviews for quality     │
│  → shows preview for user approval                   │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  5. PUBLISH                                          │
│  • Edit individual quizzes                           │
│  • Publish all at once                               │
│  • Or schedule gradual publication (e.g. 5min gaps)  │
└─────────────────────────────────────────────────────┘
```

---

---

## 📁 Project Structure

```
BotDeEncuestas/
├── bot/                  ← Main application package
│   ├── main.py           ← Entry point
│   ├── config.py         ← Settings & env vars
│   ├── handlers/         ← Telegram message/callback handlers
│   ├── services/         ← AI service integration
│   ├── database/         ← Async SQLite layer
│   ├── keyboards/        ← Inline keyboard builders
│   ├── middleware/        ← Whitelist & access control
│   └── states/           ← FSM state definitions
├── pyproject.toml        ← Project metadata & build config (Hatchling)
├── uv.lock               ← Dependency lockfile
├── .env.example          ← Environment template
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Language** | Python 3.10+ |
| **Telegram Framework** | [aiogram 3.x](https://docs.aiogram.dev) (async) |
| **Database** | SQLite via [aiosqlite](https://github.com/omnilib/aiosqlite) |
| **HTTP Client** | [httpx](https://www.python-httpx.org) (async) |
| **Config** | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) + python-dotenv |
| **Proxy** | [aiohttp-socks](https://github.com/romis2012/aiohttp-socks) (SOCKS5/HTTP) |
| **Build** | [Hatchling](https://hatch.pypa.io) |
| **Package Manager** | [uv](https://docs.astral.sh/uv/) |

---

## 📄 License

MIT

---

<div align="center">

**Built with ❤️ by [@somesupercoder](https://github.com/somesupercoder)**

</div>
