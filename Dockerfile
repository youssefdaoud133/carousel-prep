# syntax=docker/dockerfile:1
# Carousel Prep: one image that serves the web app and the image-processing API.

# --- Web app (static files): built once on the build machine's own platform ---------
FROM --platform=$BUILDPLATFORM node:26.13.0-trixie-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci
COPY frontend/ ./
RUN npm run build

# --- App: Python API that also serves the web app ----------------------------------
FROM python:3.15.2-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, so they stay cached between code changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

COPY backend/ /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

COPY --from=web /web/dist /app/static

ENV PATH="/app/.venv/bin:$PATH" \
    STATIC_DIR=/app/static

RUN useradd --system --no-create-home app
USER app

EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health')"]

LABEL org.opencontainers.image.title="Carousel Prep" \
      org.opencontainers.image.description="Prepare photos for Instagram carousels: seamless panorama splits, 4:5 slides, logo, ZIP export." \
      org.opencontainers.image.source="https://github.com/youssefdaoud133/carousel-prep"

# One process on purpose: upload sessions live in memory.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]
