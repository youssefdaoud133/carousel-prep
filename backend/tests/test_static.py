"""Serving the built frontend from the API process (single-image deployment)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.static import mount_frontend


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>Carousel Prep</title>")
    (tmp_path / "assets" / "app-abc123.js").write_text("console.log('hi')")
    (tmp_path / "favicon.ico").write_bytes(b"\x00\x00\x01\x00")
    (tmp_path / "manifest.webmanifest").write_text("{}")

    app = FastAPI()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    mount_frontend(app, tmp_path)
    with TestClient(app) as c:
        yield c


def test_index_is_served_without_caching(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "Carousel Prep" in r.text
    assert r.headers["cache-control"] == "no-cache"


def test_unknown_page_routes_fall_back_to_the_app(client: TestClient) -> None:
    r = client.get("/some/page")
    assert r.status_code == 200
    assert "Carousel Prep" in r.text


def test_hashed_assets_are_cached_forever(client: TestClient) -> None:
    r = client.get("/assets/app-abc123.js")
    assert r.status_code == 200
    assert "immutable" in r.headers["cache-control"]


def test_public_files_are_served(client: TestClient) -> None:
    assert client.get("/favicon.ico").status_code == 200
    r = client.get("/manifest.webmanifest")
    assert r.headers["content-type"].startswith("application/manifest+json")


def test_missing_files_are_404_not_the_app(client: TestClient) -> None:
    assert client.get("/missing.png").status_code == 404
    assert client.get("/assets/nope.js").status_code == 404


def test_api_routes_still_win(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/unknown").status_code == 404


def test_path_traversal_is_rejected(client: TestClient, tmp_path: Path) -> None:
    (tmp_path.parent / "secret.txt").write_text("nope")
    r = client.get("/..%2Fsecret.txt")
    assert r.status_code == 404
    assert "nope" not in r.text
