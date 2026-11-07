"""Generate every logo asset the project uses from the source PNG.

Run from the repo root:

    uv run --project backend python logo/build_assets.py

Outputs:
  logo/carousel-prep-icon.png        cleaned + trimmed icon, light backgrounds
  logo/carousel-prep-icon-dark.png   same icon recolored for dark backgrounds
  frontend/src/assets/logo*.png      header logo (light/dark)
  frontend/public/favicon.ico        16/32/48 on a light tile (readable on any tab bar)
  frontend/public/apple-touch-icon.png, icon-192.png, icon-512.png, icon-maskable-512.png
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "logo" / "Split Panorama Carousel Icon.png"

INK_LIGHT = (0xF5, 0xF5, 0xF5)  # dark-mode ink
SHEET_DARK = (0x12, 0x12, 0x12)  # dark-mode surface
TILE = (0xFF, 0xFF, 0xFF)  # light app surface

# Instagram brand gradient, applied top -> bottom along the dashed cut line.
IG_GRADIENT = [
    (0.00, (0x83, 0x3A, 0xB4)),
    (0.25, (0xC1, 0x35, 0x84)),
    (0.50, (0xE1, 0x30, 0x6C)),
    (0.70, (0xFD, 0x1D, 0x1D)),
    (0.85, (0xF7, 0x77, 0x37)),
    (1.00, (0xFC, 0xAF, 0x45)),
]


def clean(img: Image.Image) -> Image.Image:
    """Drop near-invisible generator noise and trim to the artwork."""
    img = img.convert("RGBA")
    alpha = img.getchannel("A").point(lambda a: 0 if a < 8 else a)
    img.putalpha(alpha)
    return img.crop(alpha.getbbox())


def square(img: Image.Image, size: int, padding: float, bg=None, radius: float = 0) -> Image.Image:
    """Center the icon on a square canvas with relative padding, optionally on a rounded tile."""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if bg is not None:
        tile = Image.new("L", (size, size), 0)
        ImageDraw.Draw(tile).rounded_rectangle(
            [0, 0, size - 1, size - 1], radius=round(size * radius), fill=255
        )
        canvas.paste(Image.new("RGBA", (size, size), (*bg, 255)), (0, 0), tile)
    inner = round(size * (1 - 2 * padding))
    icon = img.copy()
    icon.thumbnail((inner, inner), Image.Resampling.LANCZOS)
    canvas.alpha_composite(icon, ((size - icon.width) // 2, (size - icon.height) // 2))
    return canvas


def cut_mask(img: Image.Image) -> list[bool]:
    """Which pixels belong to the red dashed cut line (strongly red, visible)."""
    return [a > 0 and r - max(g, b) > 60 for r, g, b, a in img.get_flattened_data()]


def gradient_at(t: float) -> tuple[int, int, int]:
    for (t0, c0), (t1, c1) in zip(IG_GRADIENT, IG_GRADIENT[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0)
            return tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
    return IG_GRADIENT[-1][1]


def paint_cut(img: Image.Image, mask: list[bool]) -> Image.Image:
    """Recolor the cut line with the Instagram gradient, keeping its anti-aliased alpha."""
    w = img.width
    rows = [i // w for i, m in enumerate(mask) if m]
    top, bottom = min(rows), max(rows)
    out = img.copy()
    px = out.load()
    for i, m in enumerate(mask):
        if m:
            x, y = i % w, i // w
            px[x, y] = (*gradient_at((y - top) / max(1, bottom - top)), px[x, y][3])
    return out


def recolor_dark(img: Image.Image, mask: list[bool]) -> Image.Image:
    """Black ink -> light ink, light fills -> dark surface; the cut line is left as is."""
    out = []
    for (r, g, b, a), is_cut in zip(img.get_flattened_data(), mask):
        if a == 0:
            out.append((0, 0, 0, 0))
            continue
        if is_cut:
            out.append((r, g, b, a))
            continue
        t = (0.299 * r + 0.587 * g + 0.114 * b) / 236  # 0 = black ink, 1 = light fill
        t = min(max(t, 0.0), 1.0)
        mixed = tuple(round(ink + (sheet - ink) * t) for ink, sheet in zip(INK_LIGHT, SHEET_DARK))
        out.append((*mixed, a))
    dark = Image.new("RGBA", img.size)
    dark.putdata(out)
    return dark


def main() -> None:
    source = clean(Image.open(SOURCE))
    mask = cut_mask(source)
    icon = paint_cut(source, mask)
    dark = paint_cut(recolor_dark(source, mask), mask)

    logo_dir = ROOT / "logo"
    square(icon, 1024, 0.06).save(logo_dir / "carousel-prep-icon.png", optimize=True)
    square(dark, 1024, 0.06).save(logo_dir / "carousel-prep-icon-dark.png", optimize=True)

    # Header logo: trimmed, 3x of a 28 px display height.
    assets = ROOT / "frontend" / "src" / "assets"
    assets.mkdir(exist_ok=True)
    for name, img in (("logo.png", icon), ("logo-dark.png", dark)):
        small = img.copy()
        small.thumbnail((10_000, 84), Image.Resampling.LANCZOS)
        small.save(assets / name, optimize=True)

    # Browser / home-screen icons on a light rounded tile so they read on light and dark UI.
    public = ROOT / "frontend" / "public"
    tile_ico = square(icon, 256, 0.08, bg=TILE, radius=0.22)
    tile_ico.save(public / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    square(icon, 180, 0.1, bg=TILE).save(public / "apple-touch-icon.png", optimize=True)
    for size in (192, 512):
        square(icon, size, 0.1, bg=TILE, radius=0.22).save(
            public / f"icon-{size}.png", optimize=True
        )
    # Maskable icons get cropped to a circle by Android: keep the art in the 80% safe zone.
    square(icon, 512, 0.2, bg=TILE).save(public / "icon-maskable-512.png", optimize=True)

    print("Logo assets written.")


if __name__ == "__main__":
    main()
