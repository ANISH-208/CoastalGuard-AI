"""End-to-end API checks using synthetic records only; never real marine warnings."""
from datetime import datetime, timedelta, timezone


def _synthetic_payload(record_id: str, region: str = "TEST_COAST") -> dict:
    now = datetime.now(timezone.utc)
    return {
        "source_name": "SYNTHETIC_PILOT_TEST",
        "source_record_id": record_id,
        "title": "DEMO ONLY — NOT A REAL MARINE WARNING",
        "original_text": "Synthetic integration-test content. Do not use for marine decisions.",
        "region": region,
        "issued_at": now.isoformat(),
        "valid_from": (now - timedelta(minutes=5)).isoformat(),
        "valid_until": (now + timedelta(hours=2)).isoformat(),
        "source_url": None,
        "is_demo": True,
    }


def test_pilot_happy_path_then_fail_closed_on_source_failure(client):
    """A record may pass prototype checks, but must stop showing as current after failure."""
    created = client.post("/api/v1/admin/import", json=_synthetic_payload("pilot-001"))
    assert created.status_code == 201
    assert created.json()["is_demo"] is True
    assert created.json()["is_current"] is True

    listed = client.get("/api/v1/advisories", params={"region": "TEST_COAST"})
    assert listed.status_code == 200
    assert [row["source_record_id"] for row in listed.json()] == ["pilot-001"]

    failure = client.post(
        "/api/v1/admin/sources/unavailable",
        params={"source_name": "SYNTHETIC_PILOT_TEST", "reason": "Synthetic test outage"},
    )
    assert failure.status_code == 200

    # It must disappear from the default current-only list and be visibly non-current
    # when an operator explicitly asks to inspect all records.
    current_only = client.get("/api/v1/advisories")
    assert all(row["source_record_id"] != "pilot-001" for row in current_only.json())
    all_records = client.get("/api/v1/advisories", params={"include_expired": True})
    record = next(row for row in all_records.json() if row["source_record_id"] == "pilot-001")
    assert record["is_current"] is False

    health = client.get("/api/v1/operations/health").json()
    assert health["overall"] == "attention_required"
    assert health["current_advisory_count"] == 0


def test_pilot_workflow_rejects_unauthorized_admin_action(client):
    response = client.post(
        "/api/v1/admin/import",
        json=_synthetic_payload("unauthorized-001"),
        headers={"Authorization": "Bearer not-the-test-token"},
    )
    assert response.status_code == 401


def test_pilot_workflow_keeps_demo_label_and_region_filter(client):
    client.post("/api/v1/admin/import", json=_synthetic_payload("north-001", "TEST_NORTH"))
    client.post("/api/v1/admin/import", json=_synthetic_payload("south-001", "TEST_SOUTH"))

    north = client.get("/api/v1/advisories", params={"region": "TEST_NORTH"})
    assert north.status_code == 200
    assert len(north.json()) == 1
    assert north.json()[0]["is_demo"] is True
    assert north.json()[0]["source_record_id"] == "north-001"

    no_match = client.get("/api/v1/advisories", params={"region": "REAL_REGION_NOT_IN_TEST_DATA"})
    assert no_match.status_code == 200
    assert no_match.json() == []
