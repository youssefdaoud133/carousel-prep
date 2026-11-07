# Carousel Prep

Prepare photos for Instagram carousel posts: portraits stay single slides, landscapes are split into two seamless 4:5 halves, everything is renamed `title_picture_N` and exported as a ZIP, with an optional logo overlay.

## Stack

- **frontend/**: React + TypeScript + Vite + Tailwind CSS
- **backend/**: Python + FastAPI + Pillow (managed with uv)

## Run with Docker

```bash
docker compose up --build
```

Open http://localhost:8080. Use another port with `PORT=9000 docker compose up --build`.
Stop with `docker compose down`.

## Development (without Docker)

```bash
# API on :8000
cd backend && uv run carousel-prep

# UI on :5173 (proxies /api to :8000)
cd frontend && npm install && npm run dev
```

Tests and lint:

```bash
cd backend && uv run pytest && uv run ruff check .
cd frontend && npm run build && npm run lint
```
