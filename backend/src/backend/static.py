"""Serve the built frontend (Vite `dist/`) from the API process.

Used by the single Docker image: one process serves both `/api/*` and the web app.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

mimetypes.add_type("application/manifest+json", ".webmanifest")

IMMUTABLE = "public, max-age=31536000, immutable"


def mount_frontend(app: FastAPI, root: Path) -> None:
    root = root.resolve()
    index = root / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path.startswith("api/") or path == "api":
            raise HTTPException(404, "Not found")

        candidate = (root / path).resolve()
        if not candidate.is_relative_to(root):
            raise HTTPException(404, "Not found")

        if path and candidate.is_file():
            cache = IMMUTABLE if path.startswith("assets/") else "no-cache"
            return FileResponse(candidate, headers={"Cache-Control": cache})

        # A missing file (anything with an extension) is a 404, not the app shell.
        if Path(path).suffix:
            raise HTTPException(404, "Not found")

        return FileResponse(index, headers={"Cache-Control": "no-cache"})
