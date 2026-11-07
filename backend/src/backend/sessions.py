"""Temporary per-browser-session storage for uploaded photos and the logo."""

from __future__ import annotations

import shutil
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from .imaging import Orientation, classify, encode_jpeg, load_image, load_logo

SESSION_TTL_SECONDS = 2 * 60 * 60
WORKING_LONG_SIDE = 2000  # downscaled copy used for fast previews
THUMB_LONG_SIDE = 400


class NotFoundError(KeyError):
    pass


@dataclass
class StoredImage:
    id: str
    filename: str
    width: int
    height: int
    orientation: Orientation


@dataclass
class Session:
    id: str
    dir: Path
    images: dict[str, StoredImage] = field(default_factory=dict)
    has_logo: bool = False
    touched: float = field(default_factory=time.monotonic)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def path(self, image_id: str, kind: str) -> Path:
        return self.dir / f"{image_id}.{kind}"

    # --- images ---------------------------------------------------------

    def add_image(self, filename: str, data: bytes) -> StoredImage:
        img = load_image(data)  # validates + normalizes; raises ImageLoadError
        image_id = uuid.uuid4().hex
        self.path(image_id, "orig").write_bytes(data)
        _save_scaled(img, WORKING_LONG_SIDE, self.path(image_id, "work.jpg"))
        _save_scaled(img, THUMB_LONG_SIDE, self.path(image_id, "thumb.jpg"))
        stored = StoredImage(image_id, filename, img.width, img.height, classify(img.size))
        with self.lock:
            self.images[image_id] = stored
        return stored

    def get_image(self, image_id: str) -> StoredImage:
        try:
            return self.images[image_id]
        except KeyError:
            raise NotFoundError(f"Image {image_id} not found") from None

    def remove_image(self, image_id: str) -> None:
        self.get_image(image_id)
        with self.lock:
            del self.images[image_id]
        for kind in ("orig", "work.jpg", "thumb.jpg"):
            self.path(image_id, kind).unlink(missing_ok=True)

    def open_image(self, image_id: str, *, full: bool) -> Image.Image:
        self.get_image(image_id)
        if full:
            return load_image(self.path(image_id, "orig").read_bytes())
        return Image.open(self.path(image_id, "work.jpg")).convert("RGB")

    def thumb_path(self, image_id: str) -> Path:
        self.get_image(image_id)
        return self.path(image_id, "thumb.jpg")

    # --- logo -----------------------------------------------------------

    def set_logo(self, data: bytes) -> Image.Image:
        logo = load_logo(data)
        logo.save(self.dir / "logo.png")
        self.has_logo = True
        return logo

    def remove_logo(self) -> None:
        (self.dir / "logo.png").unlink(missing_ok=True)
        self.has_logo = False

    def open_logo(self) -> Image.Image | None:
        if not self.has_logo:
            return None
        return Image.open(self.dir / "logo.png").convert("RGBA")


def _save_scaled(img: Image.Image, long_side: int, dest: Path) -> None:
    copy = img.copy()
    copy.thumbnail((long_side, long_side), Image.Resampling.LANCZOS)
    dest.write_bytes(encode_jpeg(copy, quality=90))


class SessionStore:
    def __init__(self, root: Path | None = None, ttl: float = SESSION_TTL_SECONDS) -> None:
        self.root = root or Path(tempfile.mkdtemp(prefix="carousel-prep-"))
        self.ttl = ttl
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self) -> Session:
        self.cleanup()
        session_id = uuid.uuid4().hex
        directory = self.root / session_id
        directory.mkdir(parents=True)
        session = Session(session_id, directory)
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise NotFoundError("Session expired or not found")
        session.touched = time.monotonic()
        return session

    def cleanup(self) -> None:
        cutoff = time.monotonic() - self.ttl
        with self._lock:
            expired = [s for s in self._sessions.values() if s.touched < cutoff]
            for s in expired:
                del self._sessions[s.id]
        for s in expired:
            shutil.rmtree(s.dir, ignore_errors=True)
