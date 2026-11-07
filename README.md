# Carousel Prep

Prepare photos for an Instagram carousel post in one pass:

- **Portraits** become one slide each.
- **Landscapes** are cut into two slides that line up exactly, so swiping from one to the next
  reads as one continuous picture.
- Every slide is **1080 × 1350 (4:5)**, Instagram's tallest portrait format. Instagram crops all
  slides in a carousel to the first slide's shape, so they all share one size.
- Files are named from the post title in carousel order: `lisbon_weekend_picture_1.jpg`,
  `lisbon_weekend_picture_2.jpg`, … and downloaded as `lisbon_weekend.zip`, containing a
  `lisbon_weekend/` folder.
- An optional **logo** goes in a chosen corner with adjustable size, margin and opacity. On a split
  landscape it appears once, at the outer edge of the full photo: on the first half for left
  corners, on the second half for right corners.

## Run

```bash
docker compose up --build
```

Open http://localhost:8080. To use another port: `PORT=9000 docker compose up --build`.
Stop with `docker compose down`.

## How to use

1. Drop photos anywhere on the page (JPG, PNG, WebP or HEIC, up to 50 MB each, 40 per post).
2. Drag the photo cards into carousel order. With the keyboard: focus a card, press Space, move
   with the arrow keys and press Space again.
3. Enter a post title. The file names update as you type.
4. Choose how portraits that aren't 4:5 are handled: **Crop to fill**, or **Fit with border**
   (white, black or a blurred copy of the photo).
5. Optional: use the crop button on a photo card to move the crop window. For landscapes this
   also moves where the swipe cut falls.
6. Optional: turn on **Logo**, upload a PNG and pick its corner, size, margin and opacity.
7. Click any preview slide to flip through the carousel as it will appear on a phone.
8. Click **Export ZIP**.

### How cropping works

- A landscape is center-cropped to 8:5 (two 4:5 slides side by side), resized to 2160 × 1350
  and cut down the middle. A 3:2 photo loses about 6% at the top and bottom; a 16:9 photo loses
  about 10% at the sides.
- Photos are rotated using their EXIF orientation and converted to sRGB. Output is JPEG at
  quality 95 with full chroma resolution (4:4:4).

## Stack

| Part | Tech |
| --- | --- |
| `frontend/` | React 19, TypeScript 7, Vite 8, Tailwind CSS 4, dnd-kit; served by nginx in Docker |
| `backend/` | Python 3.15, FastAPI, Pillow 13, pillow-heif; managed with uv |

The backend keeps uploads in a temporary per-browser session (cleared after 2 hours idle).
Nothing is written outside the container.

### API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/sessions` | Start a session |
| `POST` | `/api/sessions/{id}/images` | Upload photos (multipart `files`) |
| `GET` | `/api/sessions/{id}/images/{image}/thumb` | Thumbnail |
| `DELETE` | `/api/sessions/{id}/images/{image}` | Remove a photo |
| `PUT` / `DELETE` | `/api/sessions/{id}/logo` | Set or remove the logo |
| `POST` | `/api/sessions/{id}/preview` | Render small preview slides |
| `POST` | `/api/sessions/{id}/export` | Render full-size slides as a ZIP |

## Development (without Docker)

```bash
# API on :8000
cd backend && uv run carousel-prep

# UI on :5173 (proxies /api to :8000)
cd frontend && npm install && npm run dev
```

Tests and lint:

```bash
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd frontend && npm run build && npm run lint
```
