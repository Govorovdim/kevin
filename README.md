# Kevin

Household financial planner — track income, expenses, assets, and liabilities, with an AI chatbot (Google Gemini) to query and manage your finances. Built with **FastAPI** and **React Native (Expo)**.

## Demo

A deployed demo is available at https://wackyduckling.com/kevin/

- **User:** demo
- **Password:** password

## Features

- Multi-household support with QR code invites
- Monthly tracking of income, expenses, assets, and liabilities
- Yearly overview with interactive charts
- AI chatbot powered by Google Gemini:
  - Ask it to find or calculate something across your finances
  - Add new income, expense, asset, or liability entries
  - Update existing entries
- Excel import/export
- Stock ticker search via Yahoo Finance
- Cross-platform (iOS, Android, Web)

## Tech Stack

- **Backend:** FastAPI, SQLModel, PostgreSQL, Alembic, JWT auth, Google Gemini
- **Frontend:** React Native / Expo, Expo Router, NativeWind, TanStack Query, Zustand

## Getting Started

### Prerequisites

- Python 3.13+ with [uv](https://docs.astral.sh/uv/)
- Node.js 18+
- Docker

### Setup

```bash
# Configure environment
cp .env.example .env
# Set KEVIN_SECRET_KEY in .env (python -c "import secrets; print(secrets.token_urlsafe(32))")
# Set KEVIN_GEMINI_API_KEY in .env to enable the AI chatbot (https://aistudio.google.com/apikey)

# Start database
docker compose up -d

# Backend
uv sync
uv run alembic upgrade head
uv run start
# API at http://localhost:8000 — docs at http://localhost:8000/docs

# Frontend
cd kevin-ui
npm install
npx expo start
```

### AI Chatbot (Gemini)

The chat assistant is served from `POST /api/v1/chat/` and backed by Google Gemini.

1. **Generate a key** — create a Google Gemini API key at https://aistudio.google.com/apikey.
2. **Add it to `.env`** — set `KEVIN_GEMINI_API_KEY=<your-key>`. Required for chat; without it, requests fail with HTTP 502.
3. **Pick a model** (optional) — set `KEVIN_GEMINI_MODEL` to override the default `gemini-2.5-flash`.

### Debug Mode

Set `KEVIN_DEBUG=true` in `.env` for auto-reload and relaxed CORS (useful for physical device testing over LAN).

## License

GPL-3.0
