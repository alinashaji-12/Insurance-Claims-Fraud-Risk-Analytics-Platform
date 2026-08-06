"""API smoke tests for Phase 8 endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_claims_list():
    res = client.get("/claims", params={"page": 1, "page_size": 5})
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    assert "total" in body
    assert body["page"] == 1
    assert body["page_size"] == 5
    assert isinstance(body["items"], list)


def test_claim_not_found():
    res = client.get("/claims/99999999")
    assert res.status_code == 404


def test_stats_summary():
    res = client.get("/stats/summary")
    assert res.status_code == 200
    body = res.json()
    assert "total_claims" in body
    assert "flagged_count" in body
    assert "avg_score" in body


def test_upload_missing_columns():
    files = {"file": ("bad.csv", b"foo,bar\n1,2\n", "text/csv")}
    res = client.post("/claims/upload", files=files)
    assert res.status_code == 400
