"""Tests for the health and datasets endpoints."""

from fastapi.testclient import TestClient


def test_health_ok(empty_client: TestClient) -> None:
    response = empty_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "object_count": 0}


def test_health_reports_object_count(client: TestClient) -> None:
    assert client.get("/health").json()["object_count"] == 5


def test_datasets_empty(empty_client: TestClient) -> None:
    response = empty_client.get("/datasets")
    assert response.status_code == 200
    assert response.json() == []


def test_datasets_after_seed(client: TestClient) -> None:
    names = {dataset["name"] for dataset in client.get("/datasets").json()}
    assert "seed" in names
