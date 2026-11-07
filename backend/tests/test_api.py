import io
import zipfile
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import main
from backend.sessions import SessionStore


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setattr(main, "store", SessionStore(root=tmp_path))
    with TestClient(main.app) as c:
        yield c


def jpeg(size: tuple[int, int], color=(200, 50, 50)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return buf.getvalue()


def png_logo() -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (200, 100), (0, 0, 255, 255)).save(buf, "PNG")
    return buf.getvalue()


def new_session(client: TestClient) -> str:
    r = client.post("/api/sessions")
    assert r.status_code == 201
    return r.json()["id"]


def upload(client: TestClient, sid: str, *files: tuple[str, bytes]) -> dict:
    r = client.post(
        f"/api/sessions/{sid}/images",
        files=[("files", (name, data, "image/jpeg")) for name, data in files],
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_upload_reports_orientation_and_slide_count(client: TestClient) -> None:
    sid = new_session(client)
    body = upload(client, sid, ("p.jpg", jpeg((800, 1000))), ("l.jpg", jpeg((1500, 1000))))

    assert [(i["filename"], i["orientation"], i["slides"]) for i in body["images"]] == [
        ("p.jpg", "portrait", 1),
        ("l.jpg", "landscape", 2),
    ]
    assert body["errors"] == []


def test_upload_collects_errors_for_bad_files(client: TestClient) -> None:
    sid = new_session(client)
    body = upload(client, sid, ("ok.jpg", jpeg((800, 1000))), ("bad.txt", b"hello"))
    assert len(body["images"]) == 1
    assert body["errors"] == [{"filename": "bad.txt", "message": "Not a supported image"}]


def test_thumb_and_delete(client: TestClient) -> None:
    sid = new_session(client)
    image_id = upload(client, sid, ("p.jpg", jpeg((800, 1000))))["images"][0]["id"]

    r = client.get(f"/api/sessions/{sid}/images/{image_id}/thumb")
    assert r.status_code == 200
    assert max(Image.open(io.BytesIO(r.content)).size) == 400

    assert client.delete(f"/api/sessions/{sid}/images/{image_id}").status_code == 204
    assert client.get(f"/api/sessions/{sid}/images/{image_id}/thumb").status_code == 404


def test_unknown_session_is_404(client: TestClient) -> None:
    r = client.post("/api/sessions/nope/preview", json={"order": [{"id": "x"}]})
    assert r.status_code == 404
    assert "Session" in r.json()["detail"]


def test_preview_returns_slides_in_order_with_names(client: TestClient) -> None:
    sid = new_session(client)
    ids = [
        i["id"]
        for i in upload(client, sid, ("l.jpg", jpeg((1500, 1000))), ("p.jpg", jpeg((800, 1000))))[
            "images"
        ]
    ]
    r = client.post(
        f"/api/sessions/{sid}/preview",
        json={"order": [{"id": ids[1]}, {"id": ids[0]}], "title": "Beach Day"},
    )
    assert r.status_code == 200, r.text
    slides = r.json()["slides"]
    assert [(s["index"], s["part"], s["name"]) for s in slides] == [
        (1, "full", "beach_day_picture_1.jpg"),
        (2, "left", "beach_day_picture_2.jpg"),
        (3, "right", "beach_day_picture_3.jpg"),
    ]
    assert slides[0]["data_url"].startswith("data:image/jpeg;base64,")


def test_preview_without_title_has_no_names(client: TestClient) -> None:
    sid = new_session(client)
    image_id = upload(client, sid, ("p.jpg", jpeg((800, 1000))))["images"][0]["id"]
    r = client.post(f"/api/sessions/{sid}/preview", json={"order": [{"id": image_id}]})
    assert r.json()["slides"][0]["name"] is None


def test_preview_unknown_image_is_404(client: TestClient) -> None:
    sid = new_session(client)
    r = client.post(f"/api/sessions/{sid}/preview", json={"order": [{"id": "missing"}]})
    assert r.status_code == 404


def test_preview_rejects_invalid_settings(client: TestClient) -> None:
    sid = new_session(client)
    r = client.post(
        f"/api/sessions/{sid}/preview",
        json={"order": [{"id": "a", "focus": 2}], "fit_mode": "stretch"},
    )
    assert r.status_code == 422


def test_export_zip_contains_named_full_size_slides(client: TestClient) -> None:
    sid = new_session(client)
    ids = [
        i["id"]
        for i in upload(client, sid, ("p.jpg", jpeg((800, 1000))), ("l.jpg", jpeg((3000, 2000))))[
            "images"
        ]
    ]
    r = client.post(
        f"/api/sessions/{sid}/export",
        json={"order": [{"id": i} for i in ids], "title": "Summer 2026", "fit_mode": "pad"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/zip"
    assert 'filename="summer_2026.zip"' in r.headers["content-disposition"]

    zf = zipfile.ZipFile(io.BytesIO(r.content))
    assert zf.namelist() == [
        "summer_2026/summer_2026_picture_1.jpg",
        "summer_2026/summer_2026_picture_2.jpg",
        "summer_2026/summer_2026_picture_3.jpg",
    ]
    for name in zf.namelist():
        assert Image.open(zf.open(name)).size == (1080, 1350)


def test_export_requires_title(client: TestClient) -> None:
    sid = new_session(client)
    image_id = upload(client, sid, ("p.jpg", jpeg((800, 1000))))["images"][0]["id"]
    r = client.post(
        f"/api/sessions/{sid}/export", json={"order": [{"id": image_id}], "title": "  "}
    )
    assert r.status_code == 400
    assert "title" in r.json()["detail"]


def test_logo_upload_applies_and_removes(client: TestClient) -> None:
    sid = new_session(client)
    image_id = upload(client, sid, ("p.jpg", jpeg((800, 1000), (255, 255, 255))))["images"][0]["id"]

    r = client.put(f"/api/sessions/{sid}/logo", files={"file": ("logo.png", png_logo())})
    assert r.json() == {"width": 200, "height": 100}

    body = {
        "order": [{"id": image_id}],
        "title": "x",
        "logo": {"enabled": True, "corner": "top-left", "size_pct": 20, "margin_pct": 5},
    }
    zf = zipfile.ZipFile(io.BytesIO(client.post(f"/api/sessions/{sid}/export", json=body).content))
    slide = Image.open(zf.open(zf.namelist()[0])).convert("RGB")
    r_, g_, b_ = slide.getpixel((54 + 20, 67 + 20))
    assert b_ > 200 and r_ < 40

    assert client.delete(f"/api/sessions/{sid}/logo").status_code == 204
    zf = zipfile.ZipFile(io.BytesIO(client.post(f"/api/sessions/{sid}/export", json=body).content))
    slide = Image.open(zf.open(zf.namelist()[0])).convert("RGB")
    assert min(slide.getpixel((54 + 20, 67 + 20))) > 240


def test_logo_rejects_non_image(client: TestClient) -> None:
    sid = new_session(client)
    r = client.put(f"/api/sessions/{sid}/logo", files={"file": ("logo.png", b"nope")})
    assert r.status_code == 400


def test_expired_sessions_are_cleaned_up(tmp_path) -> None:
    store = SessionStore(root=tmp_path, ttl=-1)
    old = store.create()
    store.create()  # triggers cleanup
    assert not old.dir.exists()
