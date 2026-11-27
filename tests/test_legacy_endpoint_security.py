from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend import main as engine_api
from backend.services import storage_service as storage_module

@pytest.fixture
def security_client(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "AI_ENGINE_INTERNAL_KEY",
        "test-internal-secret",
    )

    monkeypatch.setattr(
        storage_module,
        "DATA_FOLDER",
        str(tmp_path),
    )

    with TestClient(engine_api.app) as client:
        yield client

@pytest.mark.parametrize(
    "method,path,payload",
    [
        (
            "POST",
            "/start-interview",
            {"topic": "Software Engineering"},
        ),
        (
            "POST",
            f"/interview/{uuid4()}/answer",
            {"answer": "My test answer"},
        ),
        (
            "GET",
            f"/interview/{uuid4()}",
            None,
        ),
        (
            "GET",
            f"/interview/{uuid4()}/summary",
            None,
        ),
        (
            "POST",
            f"/interview/{uuid4()}/feedback",
            None,
        ),
    ],
)
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-Internal-API-Key": "wrong-key"},
    ],
)
def test_legacy_endpoint_rejects_unauthorized_access(
    security_client,
    method,
    path,
    payload,
    headers,
):
    response = security_client.request(
        method,
        path,
        json=payload,
        headers=headers,
    )

    assert response.status_code == 403

def test_valid_internal_key_reaches_legacy_endpoint(
    security_client,
):
    response = security_client.get(
        f"/interview/{uuid4()}",
        headers={
            "X-Internal-API-Key": "test-internal-secret",
        },
    )

    assert response.status_code == 404