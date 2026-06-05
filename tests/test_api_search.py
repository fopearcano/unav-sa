"""Tests for object search, retrieval and JSONL import endpoints."""

from fastapi.testclient import TestClient

from unav_core.data import CatalogObject, ObjectType, write_jsonl


def test_search_by_name(client: TestClient) -> None:
    body = client.get("/objects/search", params={"q": "veg"}).json()
    assert body["count"] == 1
    assert body["objects"][0]["uid"] == "gaia:1"


def test_search_by_type(client: TestClient) -> None:
    objects = client.get("/objects/search", params={"object_type": "galaxy"}).json()["objects"]
    assert {o["uid"] for o in objects} == {"m87"}


def test_search_by_source(client: TestClient) -> None:
    objects = client.get("/objects/search", params={"source": "Gaia DR3"}).json()["objects"]
    assert {o["uid"] for o in objects} == {"gaia:1", "gaia:2"}


def test_search_default_lists_objects(client: TestClient) -> None:
    assert client.get("/objects/search").json()["count"] == 5


def test_search_respects_limit(client: TestClient) -> None:
    assert client.get("/objects/search", params={"limit": 2}).json()["count"] == 2


def test_get_object(client: TestClient) -> None:
    response = client.get("/objects/gaia:1")
    assert response.status_code == 200
    assert response.json()["name"] == "Vega"


def test_get_object_not_found(client: TestClient) -> None:
    assert client.get("/objects/does-not-exist").status_code == 404


def test_import_jsonl(tmp_path, empty_client: TestClient) -> None:
    path = tmp_path / "c.jsonl"
    write_jsonl(
        [CatalogObject(uid="x", source="s", object_type=ObjectType.STAR, ra_deg=1.0, dec_deg=2.0)],
        path,
    )
    response = empty_client.post(
        "/datasets/import-jsonl", json={"path": str(path), "dataset_name": "imported"}
    )
    assert response.status_code == 200
    assert response.json()["inserted"] == 1
    assert empty_client.get("/objects/x").status_code == 200
    assert {d["name"] for d in empty_client.get("/datasets").json()} == {"imported"}


def test_import_jsonl_missing_file(empty_client: TestClient) -> None:
    response = empty_client.post(
        "/datasets/import-jsonl", json={"path": "/no/such/file.jsonl", "dataset_name": "x"}
    )
    assert response.status_code == 404
