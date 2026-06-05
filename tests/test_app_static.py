"""Tests that the local server serves the standalone static UI alongside the API."""

from fastapi.testclient import TestClient

from unav_server.app import create_app


def test_serves_ui_index(empty_client: TestClient) -> None:
    response = empty_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "UNAV" in response.text


def test_serves_static_assets(empty_client: TestClient) -> None:
    assert empty_client.get("/app.js").status_code == 200
    assert empty_client.get("/style.css").status_code == 200


def test_api_coexists_with_ui(client: TestClient) -> None:
    # The static mount at "/" must not shadow the API routes.
    assert client.get("/health").status_code == 200
    assert client.get("/objects/search").status_code == 200
    assert client.get("/objects/gaia:1").status_code == 200


def test_ui_can_be_disabled() -> None:
    disabled = TestClient(create_app(":memory:", serve_ui=False))
    assert disabled.get("/").status_code == 404
    assert disabled.get("/health").status_code == 200
