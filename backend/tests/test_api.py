"""API smoke tests for Phase 8 endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_claims_list(client: TestClient):
    res = client.get("/claims", params={"page": 1, "page_size": 5})
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    assert "total" in body
    assert body["page"] == 1
    assert body["page_size"] == 5
    assert isinstance(body["items"], list)


def test_claim_not_found(client: TestClient):
    res = client.get("/claims/99999999")
    assert res.status_code == 404


def test_stats_summary(client: TestClient):
    res = client.get("/stats/summary")
    assert res.status_code == 200
    body = res.json()
    assert "total_claims" in body
    assert "flagged_count" in body
    assert "avg_score" in body
    assert "high_risk_count" in body


def test_stats_metrics(client: TestClient):
    res = client.get("/stats/metrics")
    assert res.status_code == 200
    body = res.json()
    assert "available" in body
    assert "fraud_model" in body


def test_claims_search_q(client: TestClient):
    res = client.get("/claims", params={"q": "RING-", "page": 1, "page_size": 25})
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    assert body["total"] >= 1
    for item in body["items"]:
        blob = f"{item['policy_number']} {item['claimant_name']}".upper()
        assert "RING-" in blob


def test_upload_missing_columns(client: TestClient):
    files = {"file": ("bad.csv", b"foo,bar\n1,2\n", "text/csv")}
    res = client.post("/claims/upload", files=files)
    assert res.status_code == 400
