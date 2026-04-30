from __future__ import annotations

import base64
from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.core.config import get_settings
from api.core.inference import get_predictor
from api.core.storage import get_history_store


TINY_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5g1r8AAAAASUVORK5CYII="
)


def _build_image_bytes() -> bytes:
    return base64.b64decode(TINY_PNG_BASE64)


@pytest.fixture(autouse=True)
def reset_backend_state() -> None:
    get_predictor.cache_clear()
    get_history_store.cache_clear()

    history_path = get_settings().history_db_path
    if history_path.exists():
        history_path.unlink()

    yield

    get_predictor.cache_clear()
    get_history_store.cache_clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "online"}


def test_redocs_redirect_is_available(client: TestClient) -> None:
    response = client.get("/redocs", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/redoc"


def test_predict_with_image_upload_persists_history(client: TestClient) -> None:
    image_bytes = _build_image_bytes()

    response = client.post(
        "/api/v1/predict",
        files={"image": ("satellite.png", image_bytes, "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["class"]
    assert 0 <= payload["confidence"] <= 1
    assert payload["heatmap"]

    history_response = client.get("/api/v1/history")
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload["total"] == 1
    assert history_payload["items"][0]["class"] == payload["class"]


def test_predict_with_base64_form_field_supports_filters(client: TestClient) -> None:
    image_bytes = _build_image_bytes()
    image_base64 = base64.b64encode(image_bytes).decode("ascii")

    response = client.post(
        "/api/v1/predict",
        data={"image_base64": f"data:image/png;base64,{image_base64}"},
    )

    assert response.status_code == 200
    payload = response.json()

    today = date.today().isoformat()
    filtered_response = client.get("/api/v1/history", params={"date": today, "class": payload["class"]})

    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert filtered_payload["total"] == 1
    assert filtered_payload["items"][0]["class"] == payload["class"]