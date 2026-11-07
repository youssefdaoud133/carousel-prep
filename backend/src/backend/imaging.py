"""Pure image-processing functions for building Instagram carousel slides.

Every slide has the same size (4:5, 1080x1350 by default) because Instagram crops all
carousel slides to the first slide's aspect ratio. Portraits become a single slide;
landscapes are cropped to a double-width canvas and split in half so the two slides join
seamlessly when swiping.
"""

from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

import pillow_heif
from PIL import Image, ImageCms, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError

pillow_heif.register_heif_opener()

# Allow large panoramas / high-MP phone shots, but still guard against decompression bombs.
Image.MAX_IMAGE_PIXELS = 150_000_000

SLIDE_SIZE: tuple[int, int] = (1080, 1350)
RESAMPLE = Image.Resampling.LANCZOS
JPEG_QUALITY = 95

_SRGB = ImageCms.createProfile("sRGB")
_SRGB_ICC = ImageCms.ImageCmsProfile(_SRGB).tobytes()

Size = tuple[int, int]
Box = tuple[int, int, int, int]


class ImageLoadError(ValueError):
    """Raised when uploaded bytes cannot be decoded as an image."""


class Orientation(StrEnum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class FitMode(StrEnum):
    CROP = "crop"
    PAD = "pad"


class PadColor(StrEnum):
    WHITE = "white"
    BLACK = "black"
    BLUR = "blur"


class Corner(StrEnum):
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"


@dataclass(frozen=True)
class RenderSettings:
    size: Size = SLIDE_SIZE
    fit_mode: FitMode = FitMode.CROP
    pad_color: PadColor = PadColor.WHITE


@dataclass(frozen=True)
class LogoSettings:
    corner: Corner = Corner.BOTTOM_RIGHT
    size_pct: float = 15.0  # logo width as % of slide width
    margin_pct: float = 4.0  # distance from both edges as % of slide width
    opacity: int = 100  # 0-100


@dataclass(frozen=True)
class Source:
    image: Image.Image
    focus: float = 0.5  # 0 = keep left/top, 0.5 = center, 1 = keep right/bottom


# --- loading ----------------------------------------------------------------


def load_image(data: bytes) -> Image.Image:
    """Decode bytes into an upright, sRGB, RGB image."""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError) as exc:
        raise ImageLoadError("Unsupported or corrupted image file") from exc

    icc = img.info.get("icc_profile")
    img = ImageOps.exif_transpose(img)

    if img.mode == "CMYK":
        return _to_srgb(img, icc) if icc else img.convert("RGB")

    if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        img = Image.new("RGB", rgba.size, (255, 255, 255))
        img.paste(rgba, mask=rgba.getchannel("A"))
    elif img.mode != "RGB":
        img = img.convert("RGB")

    return _to_srgb(img, icc) if icc else img


def _to_srgb(img: Image.Image, icc: bytes) -> Image.Image:
    try:
        src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        return ImageCms.profileToProfile(img, src, _SRGB, outputMode="RGB")
    except ImageCms.PyCMSError, OSError, ValueError:
        return img.convert("RGB")


def load_logo(data: bytes) -> Image.Image:
    """Decode a logo, keeping its alpha channel."""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError) as exc:
        raise ImageLoadError("Unsupported or corrupted logo file") from exc
    return ImageOps.exif_transpose(img).convert("RGBA")


# --- geometry ---------------------------------------------------------------


def classify(size: Size) -> Orientation:
    w, h = size
    return Orientation.LANDSCAPE if w > h else Orientation.PORTRAIT


def crop_box(size: Size, ratio: float, focus: float = 0.5) -> Box:
    """Largest box with the given width/height ratio, positioned along the trimmed axis."""
    w, h = size
    focus = min(max(focus, 0.0), 1.0)
    if w / h > ratio:
        new_w = round(h * ratio)
        left = round((w - new_w) * focus)
        return (left, 0, left + new_w, h)
    new_h = round(w / ratio)
    top = round((h - new_h) * focus)
    return (0, top, w, top + new_h)


def _cover(img: Image.Image, size: Size, focus: float = 0.5) -> Image.Image:
    w, h = size
    return img.crop(crop_box(img.size, w / h, focus)).resize(size, RESAMPLE)


def split_landscape(img: Image.Image, size: Size, focus: float = 0.5) -> tuple[Image.Image, ...]:
    """Crop to a double-width canvas and cut it into two slides that join seamlessly."""
    w, h = size
    canvas = img.crop(crop_box(img.size, 2 * w / h, focus)).resize((2 * w, h), RESAMPLE)
    return canvas.crop((0, 0, w, h)), canvas.crop((w, 0, 2 * w, h))


def fit_portrait(
    img: Image.Image, size: Size, mode: FitMode, pad: PadColor, focus: float = 0.5
) -> Image.Image:
    if mode is FitMode.CROP:
        return _cover(img, size, focus)

    w, h = size
    scale = min(w / img.width, h / img.height)
    fg_size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    fg = img.resize(fg_size, RESAMPLE)

    if pad is PadColor.BLUR:
        bg = _cover(img, size).filter(ImageFilter.GaussianBlur(radius=max(w, h) / 30))
        bg = ImageEnhance.Brightness(bg).enhance(0.85)
    else:
        bg = Image.new("RGB", size, (255, 255, 255) if pad is PadColor.WHITE else (0, 0, 0))

    bg.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
    return bg


# --- logo -------------------------------------------------------------------


def apply_logo(slide: Image.Image, logo: Image.Image, settings: LogoSettings) -> Image.Image:
    """Return a copy of the slide with the logo composited in the chosen corner."""
    sw, sh = slide.size
    margin = round(sw * settings.margin_pct / 100)
    target_w = max(1, round(sw * settings.size_pct / 100))
    target_h = max(1, round(logo.height * target_w / logo.width))

    # Keep very tall logos inside the slide.
    max_h = max(1, sh - 2 * margin)
    if target_h > max_h:
        target_w = max(1, round(target_w * max_h / target_h))
        target_h = max_h

    mark = logo.convert("RGBA").resize((target_w, target_h), RESAMPLE)
    opacity = min(max(settings.opacity, 0), 100)
    if opacity < 100:
        alpha = mark.getchannel("A").point(lambda a: a * opacity // 100)
        mark.putalpha(alpha)

    x = (
        margin
        if settings.corner in (Corner.TOP_LEFT, Corner.BOTTOM_LEFT)
        else sw - margin - target_w
    )
    y = margin if settings.corner in (Corner.TOP_LEFT, Corner.TOP_RIGHT) else sh - margin - target_h

    out = slide.copy()
    out.paste(mark, (x, y), mark)
    return out


# --- naming -----------------------------------------------------------------


def slugify(title: str) -> str:
    """Turn a post title into a safe file/folder name, keeping Unicode letters."""
    text = unicodedata.normalize("NFC", title).strip().lower()
    text = re.sub(r"[^\w-]+", "_", text)
    text = re.sub(r"[-_]*_[-_]*", "_", text)
    text = re.sub(r"-{2,}", "-", text)
    text = text.strip("_-")[:80].strip("_-")
    if not text:
        raise ValueError("Title must contain at least one letter or digit")
    return text


def output_names(title: str, count: int) -> list[str]:
    slug = slugify(title)
    return [f"{slug}_picture_{i}.jpg" for i in range(1, count + 1)]


# --- pipeline ---------------------------------------------------------------


def build_slides(
    sources: list[Source],
    settings: RenderSettings,
    logo: Image.Image | None = None,
    logo_settings: LogoSettings | None = None,
) -> list[Image.Image]:
    """Turn ordered source images into ordered carousel slides."""
    slides: list[Image.Image] = []
    for src in sources:
        if classify(src.image.size) is Orientation.LANDSCAPE:
            slides.extend(split_landscape(src.image, settings.size, src.focus))
        else:
            slides.append(
                fit_portrait(
                    src.image, settings.size, settings.fit_mode, settings.pad_color, src.focus
                )
            )

    if logo is not None and logo_settings is not None:
        slides = [apply_logo(s, logo, logo_settings) for s in slides]
    return slides


def encode_jpeg(img: Image.Image, quality: int = JPEG_QUALITY) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(
        buf, "JPEG", quality=quality, subsampling=0, optimize=True, icc_profile=_SRGB_ICC
    )
    return buf.getvalue()
