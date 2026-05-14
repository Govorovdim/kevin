# Kevin

Household financial planner — track income, expenses, assets, and liabilities. Built with **FastAPI** and **React Native (Expo)**.

## Demo

A deployed demo is available at https://govorovdim.github.io/kevin-ui/

- **User:** demo
- **Password:** password

## Features

- Multi-household support with QR code invites
- Monthly tracking of income, expenses, assets, and liabilities
- Yearly overview with interactive charts
- Excel import/export
- Stock ticker search via Yahoo Finance
- Cross-platform (iOS, Android, Web)

## Tech Stack

- **Backend:** FastAPI, SQLModel, PostgreSQL, Alembic, JWT auth
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

### Debug Mode

Set `KEVIN_DEBUG=true` in `.env` for auto-reload and relaxed CORS (useful for physical device testing over LAN).

## License

GPL-3.0
