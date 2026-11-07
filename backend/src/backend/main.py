from __future__ import annotations

import base64
import io
import os
import zipfile
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

from .imaging import (
    ImageLoadError,
    Orientation,
    RenderSettings,
    Source,
    build_slides,
    encode_jpeg,
    output_names,
    slugify,
)
from .schemas import (
    ImageInfo,
    LogoInfo,
    PreviewResult,
    PreviewSlide,
    RenderRequest,
    SessionInfo,
    UploadError,
    UploadResult,
)
from .sessions import NotFoundError, Session, SessionStore, StoredImage
from .static import mount_frontend

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_IMAGES = 40
PREVIEW_SIZE = (540, 675)

app = FastAPI(title="Carousel Prep API")
app.add_middleware(GZipMiddleware, minimum_size=1024)
store = SessionStore()


@app.exception_handler(NotFoundError)
async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": exc.args[0]})


@app.exception_handler(ImageLoadError)
async def bad_image_handler(_: Request, exc: ImageLoadError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


def _info(img: StoredImage) -> ImageInfo:
    slides = 2 if img.orientation is Orientation.LANDSCAPE else 1
    return ImageInfo(
        id=img.id,
        filename=img.filename,
        width=img.width,
        height=img.height,
        orientation=img.orientation,
        slides=slides,
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/sessions", status_code=201)
def create_session() -> SessionInfo:
    return SessionInfo(id=store.create().id)


# --- images -------------------------------------------------------------------


@app.post("/api/sessions/{session_id}/images")
async def upload_images(
    session_id: str, files: Annotated[list[UploadFile], File(description="Photos")]
) -> UploadResult:
    session = store.get(session_id)
    images: list[ImageInfo] = []
    errors: list[UploadError] = []

    for upload in files:
        name = upload.filename or "image"
        if len(session.images) >= MAX_IMAGES:
            errors.append(UploadError(filename=name, message=f"Limit of {MAX_IMAGES} photos"))
            continue
        data = await upload.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            errors.append(UploadError(filename=name, message="File is larger than 50 MB"))
            continue
        try:
            stored = await run_in_threadpool(session.add_image, name, data)
        except ImageLoadError:
            errors.append(UploadError(filename=name, message="Not a supported image"))
            continue
        images.append(_info(stored))

    return UploadResult(images=images, errors=errors)


@app.get("/api/sessions/{session_id}/images/{image_id}/thumb")
def image_thumb(session_id: str, image_id: str) -> FileResponse:
    path = store.get(session_id).thumb_path(image_id)
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "max-age=3600"})


@app.delete("/api/sessions/{session_id}/images/{image_id}", status_code=204)
def delete_image(session_id: str, image_id: str) -> None:
    store.get(session_id).remove_image(image_id)


# --- logo ---------------------------------------------------------------------


@app.put("/api/sessions/{session_id}/logo")
async def upload_logo(session_id: str, file: Annotated[UploadFile, File()]) -> LogoInfo:
    session = store.get(session_id)
    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(400, "Logo is larger than 50 MB")
    logo = await run_in_threadpool(session.set_logo, data)
    return LogoInfo(width=logo.width, height=logo.height)


@app.delete("/api/sessions/{session_id}/logo", status_code=204)
def delete_logo(session_id: str) -> None:
    store.get(session_id).remove_logo()


# --- rendering ----------------------------------------------------------------


def _render(session: Session, req: RenderRequest, *, full: bool) -> list:
    size = RenderSettings().size if full else PREVIEW_SIZE
    sources = [
        Source(session.open_image(item.id, full=full), focus=item.focus) for item in req.order
    ]
    logo = session.open_logo() if req.logo.enabled else None
    return build_slides(
        sources,
        RenderSettings(size=size, fit_mode=req.fit_mode, pad_color=req.pad_color),
        logo=logo,
        logo_settings=req.logo.to_settings() if logo else None,
    )


def _slide_parts(session: Session, req: RenderRequest) -> list[tuple[str, str]]:
    parts: list[tuple[str, str]] = []
    for item in req.order:
        if session.get_image(item.id).orientation is Orientation.LANDSCAPE:
            parts += [(item.id, "left"), (item.id, "right")]
        else:
            parts.append((item.id, "full"))
    return parts


@app.post("/api/sessions/{session_id}/preview")
def preview(session_id: str, req: RenderRequest) -> PreviewResult:
    session = store.get(session_id)
    parts = _slide_parts(session, req)
    slides = _render(session, req, full=False)
    try:
        names: list[str | None] = list(output_names(req.title, len(slides)))
    except ValueError:
        names = [None] * len(slides)

    result = []
    for i, (slide, (image_id, part), name) in enumerate(zip(slides, parts, names, strict=True)):
        encoded = base64.b64encode(encode_jpeg(slide, quality=85)).decode()
        result.append(
            PreviewSlide(
                index=i + 1,
                image_id=image_id,
                part=part,
                name=name,
                data_url=f"data:image/jpeg;base64,{encoded}",
            )
        )
    return PreviewResult(slides=result)


@app.post("/api/sessions/{session_id}/export")
def export(session_id: str, req: RenderRequest) -> Response:
    session = store.get(session_id)
    try:
        slug = slugify(req.title)
    except ValueError as exc:
        raise HTTPException(400, "Enter a post title with at least one letter or digit") from exc

    slides = _render(session, req, full=True)
    names = output_names(req.title, len(slides))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for slide, name in zip(slides, names, strict=True):
            zf.writestr(f"{slug}/{name}", encode_jpeg(slide))

    filename = f"{slug}.zip"
    fallback = filename if filename.isascii() else "carousel.zip"
    disposition = f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename)}"
    return Response(
        buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": disposition, "X-Slide-Count": str(len(slides))},
    )


# Single-image deployment: serve the built web app from this process too.
# Registered last so its catch-all route never shadows the API.
if static_dir := os.environ.get("STATIC_DIR"):
    mount_frontend(app, Path(static_dir))
