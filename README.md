# Carousel Prep

Prepare photos for Instagram carousel posts: portraits stay single slides, landscapes are split into two seamless 4:5 halves, everything is renamed `title_picture_N` and exported as a ZIP, with an optional logo overlay.

## Stack

- **frontend/**: React + TypeScript + Vite + Tailwind CSS
- **backend/**: Python + FastAPI + Pillow (managed with uv)

## Development (without Docker)

```bash
# API on :8000
cd backend && uv run carousel-prep

# UI on :5173 (proxies /api to :8000)
cd frontend && npm install && npm run dev
```

Docker setup follows in a later step.
