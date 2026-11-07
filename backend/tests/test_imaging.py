import io

import pytest
from PIL import Image

from backend.imaging import (
    SLIDE_SIZE,
    Corner,
    FitMode,
    ImageLoadError,
    LogoSettings,
    Orientation,
    PadColor,
    RenderSettings,
    Source,
    apply_logo,
    build_slides,
    classify,
    crop_box,
    encode_jpeg,
    fit_portrait,
    load_image,
    output_names,
    slugify,
    split_landscape,
)

W, H = SLIDE_SIZE


def solid(size: tuple[int, int], color: tuple[int, ...], mode: str = "RGB") -> Image.Image:
    return Image.new(mode, size, color)


def gradient(size: tuple[int, int]) -> Image.Image:
    """Horizontal + vertical gradient so every region is distinguishable."""
    w, h = size
    img = Image.new("RGB", size)
    img.putdata([(x * 255 // w, y * 255 // h, 128) for y in range(h) for x in range(w)])
    return img


def to_bytes(img: Image.Image, fmt: str = "JPEG", **kwargs) -> bytes:
    buf = io.BytesIO()
    img.save(buf, fmt, **kwargs)
    return buf.getvalue()


def close(a: tuple[int, ...], b: tuple[int, ...], tol: int = 3) -> bool:
    return all(abs(x - y) <= tol for x, y in zip(a, b, strict=True))


# --- classify -------------------------------------------------------------


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        ((4000, 3000), Orientation.LANDSCAPE),
        ((1920, 1080), Orientation.LANDSCAPE),
        ((3000, 4000), Orientation.PORTRAIT),
        ((3000, 3000), Orientation.PORTRAIT),
    ],
)
def test_classify(size: tuple[int, int], expected: Orientation) -> None:
    assert classify(size) == expected


# --- crop_box -------------------------------------------------------------


def test_crop_box_3_2_to_8_5_trims_top_and_bottom_evenly() -> None:
    assert crop_box((6000, 4000), 8 / 5) == (0, 125, 6000, 3875)


def test_crop_box_16_9_to_8_5_trims_sides_evenly() -> None:
    assert crop_box((1920, 1080), 8 / 5) == (96, 0, 1824, 1080)


def test_crop_box_exact_ratio_keeps_everything() -> None:
    assert crop_box((2160, 1350), 8 / 5) == (0, 0, 2160, 1350)


@pytest.mark.parametrize(("focus", "left"), [(0.0, 0), (0.5, 96), (1.0, 192)])
def test_crop_box_focus_shifts_window(focus: float, left: int) -> None:
    box = crop_box((1920, 1080), 8 / 5, focus=focus)
    assert box == (left, 0, left + 1728, 1080)


# --- landscape split ------------------------------------------------------


def test_split_landscape_returns_two_slides_of_target_size() -> None:
    left, right = split_landscape(gradient((600, 400)), SLIDE_SIZE)
    assert left.size == right.size == SLIDE_SIZE


def test_split_landscape_halves_join_seamlessly() -> None:
    src = gradient((1920, 1080))
    left, right = split_landscape(src, SLIDE_SIZE)

    joined = Image.new("RGB", (2 * W, H))
    joined.paste(left, (0, 0))
    joined.paste(right, (W, 0))

    expected = src.crop(crop_box(src.size, 2 * W / H)).resize((2 * W, H), Image.Resampling.LANCZOS)
    assert joined.tobytes() == expected.tobytes()


# --- portrait fit ---------------------------------------------------------


def test_portrait_crop_removes_excess_height() -> None:
    # 2:3 image with red bands in the outer 100px top and bottom; 4:5 crop trims 125px each.
    img = solid((1000, 1500), (0, 0, 255))
    img.paste((255, 0, 0), (0, 0, 1000, 100))
    img.paste((255, 0, 0), (0, 1400, 1000, 1500))

    out = fit_portrait(img, SLIDE_SIZE, FitMode.CROP, PadColor.WHITE)

    assert out.size == SLIDE_SIZE
    assert close(out.getpixel((W // 2, 2)), (0, 0, 255))
    assert close(out.getpixel((W // 2, H - 3)), (0, 0, 255))


@pytest.mark.parametrize(
    ("pad", "corner_color"), [(PadColor.WHITE, (255, 255, 255)), (PadColor.BLACK, (0, 0, 0))]
)
def test_portrait_pad_solid_colors(pad: PadColor, corner_color: tuple[int, int, int]) -> None:
    img = solid((1000, 1500), (0, 0, 255))  # narrower than 4:5 -> bars left/right
    out = fit_portrait(img, SLIDE_SIZE, FitMode.PAD, pad)

    assert out.size == SLIDE_SIZE
    assert out.getpixel((0, H // 2)) == corner_color
    assert out.getpixel((W - 1, H // 2)) == corner_color
    assert close(out.getpixel((W // 2, H // 2)), (0, 0, 255))


def test_portrait_pad_square_adds_bars_top_and_bottom() -> None:
    out = fit_portrait(solid((800, 800), (0, 0, 255)), SLIDE_SIZE, FitMode.PAD, PadColor.BLACK)
    assert out.getpixel((W // 2, 0)) == (0, 0, 0)
    assert close(out.getpixel((0, H // 2)), (0, 0, 255))


def test_portrait_pad_blur_background_comes_from_photo() -> None:
    out = fit_portrait(solid((1000, 1500), (0, 200, 0)), SLIDE_SIZE, FitMode.PAD, PadColor.BLUR)
    r, g, b = out.getpixel((0, H // 2))
    assert g > 100 and r < 60 and b < 60


def test_portrait_exact_ratio_is_only_resized() -> None:
    src = gradient((432, 540))
    out = fit_portrait(src, SLIDE_SIZE, FitMode.PAD, PadColor.WHITE)
    assert out.size == SLIDE_SIZE
    assert out.getpixel((0, 0)) != (255, 255, 255)


# --- loading --------------------------------------------------------------


def test_load_image_applies_exif_orientation() -> None:
    img = solid((400, 300), (10, 20, 30))
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90° CW on display
    loaded = load_image(to_bytes(img, exif=exif))
    assert loaded.size == (300, 400)


def test_load_image_flattens_transparency_onto_white() -> None:
    img = solid((50, 50), (255, 0, 0, 0), mode="RGBA")
    loaded = load_image(to_bytes(img, "PNG"))
    assert loaded.mode == "RGB"
    assert loaded.getpixel((0, 0)) == (255, 255, 255)


def test_load_image_converts_cmyk_to_rgb() -> None:
    loaded = load_image(to_bytes(solid((20, 20), (0, 0, 0, 0), mode="CMYK")))
    assert loaded.mode == "RGB"


def test_load_image_rejects_garbage() -> None:
    with pytest.raises(ImageLoadError):
        load_image(b"definitely not an image")


# --- logo -----------------------------------------------------------------


def red_logo() -> Image.Image:
    return solid((100, 100), (255, 0, 0, 255), mode="RGBA")


def test_logo_top_left_size_and_margin() -> None:
    slide = solid(SLIDE_SIZE, (255, 255, 255))
    out = apply_logo(slide, red_logo(), LogoSettings(Corner.TOP_LEFT, size_pct=10, margin_pct=4))

    margin, size = 43, 108  # 4% and 10% of 1080
    assert out.getpixel((margin + 2, margin + 2)) == (255, 0, 0)
    assert out.getpixel((margin + size - 3, margin + size - 3)) == (255, 0, 0)
    assert out.getpixel((margin - 2, margin - 2)) == (255, 255, 255)
    assert out.getpixel((margin + size + 2, margin + size + 2)) == (255, 255, 255)


def test_logo_bottom_right() -> None:
    slide = solid(SLIDE_SIZE, (255, 255, 255))
    out = apply_logo(
        slide, red_logo(), LogoSettings(Corner.BOTTOM_RIGHT, size_pct=10, margin_pct=4)
    )
    assert out.getpixel((W - 43 - 5, H - 43 - 5)) == (255, 0, 0)
    assert out.getpixel((W - 43 + 2, H - 43 + 2)) == (255, 255, 255)


def test_logo_opacity_blends() -> None:
    slide = solid(SLIDE_SIZE, (255, 255, 255))
    out = apply_logo(
        slide, red_logo(), LogoSettings(Corner.TOP_LEFT, size_pct=10, margin_pct=4, opacity=50)
    )
    assert close(out.getpixel((60, 60)), (255, 128, 128), tol=2)


def test_logo_does_not_mutate_input() -> None:
    slide = solid(SLIDE_SIZE, (255, 255, 255))
    apply_logo(slide, red_logo(), LogoSettings(Corner.TOP_LEFT))
    assert slide.getpixel((60, 60)) == (255, 255, 255)


# --- naming ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("title", "slug"),
    [
        ("My Trip to Paris!", "my_trip_to_paris"),
        ("  summer---2026  ", "summer-2026"),
        ("Café Ümlaut", "café_ümlaut"),
        ("a/b\\c..d", "a_b_c_d"),
    ],
)
def test_slugify(title: str, slug: str) -> None:
    assert slugify(title) == slug


@pytest.mark.parametrize("title", ["", "   ", "!!!", "..."])
def test_slugify_rejects_empty(title: str) -> None:
    with pytest.raises(ValueError):
        slugify(title)


def test_output_names() -> None:
    assert output_names("Beach Day", 3) == [
        "beach_day_picture_1.jpg",
        "beach_day_picture_2.jpg",
        "beach_day_picture_3.jpg",
    ]


# --- build_slides ---------------------------------------------------------


def test_build_slides_keeps_order_and_splits_landscapes() -> None:
    portrait = solid((800, 1000), (255, 0, 0))
    landscape = solid((1500, 1000), (0, 255, 0))
    portrait2 = solid((800, 1000), (0, 0, 255))

    slides = build_slides(
        [Source(portrait), Source(landscape), Source(portrait2)], RenderSettings()
    )

    assert len(slides) == 4
    assert all(s.size == SLIDE_SIZE for s in slides)
    colors = [s.getpixel((W // 2, H // 2)) for s in slides]
    expected = [(255, 0, 0), (0, 255, 0), (0, 255, 0), (0, 0, 255)]
    assert all(close(c, e) for c, e in zip(colors, expected, strict=True))


def test_build_slides_custom_size_for_previews() -> None:
    slides = build_slides([Source(solid((1500, 1000), (0, 0, 0)))], RenderSettings(size=(216, 270)))
    assert [s.size for s in slides] == [(216, 270), (216, 270)]


def test_build_slides_applies_logo_to_every_slide() -> None:
    sources = [Source(solid((800, 1000), (255, 255, 255))), Source(solid((1500, 1000), (255,) * 3))]
    logo = LogoSettings(Corner.TOP_LEFT, size_pct=10, margin_pct=4)
    slides = build_slides(sources, RenderSettings(), logo=red_logo(), logo_settings=logo)
    assert all(s.getpixel((60, 60)) == (255, 0, 0) for s in slides)


# --- encoding -------------------------------------------------------------


def test_encode_jpeg_produces_srgb_jpeg() -> None:
    data = encode_jpeg(solid(SLIDE_SIZE, (1, 2, 3)))
    img = Image.open(io.BytesIO(data))
    assert img.format == "JPEG"
    assert img.size == SLIDE_SIZE
    assert img.info.get("icc_profile")
