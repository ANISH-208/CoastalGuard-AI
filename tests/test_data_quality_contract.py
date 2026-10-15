"""Data-quality contract tests; all records are synthetic and unsuitable for marine decisions."""
from datetime import datetime, timedelta, timezone


def _payload(record_id: str, **overrides) -> dict:
    now = datetime.now(timezone.utc)
    payload = {
        "source_name": "SYNTHETIC_DATA_QUALITY_TEST",
        "source_record_id": record_id,
        "title": "DEMO ONLY — NOT A REAL MARINE WARNING",
        "original_text": "Synthetic test content. Never use for marine decisions.",
        "region": "TEST_REGION",
        "issued_at": now.isoformat(),
        "valid_from": (now - timedelta(minutes=5)).isoformat(),
        "valid_until": (now + timedelta(hours=1)).isoformat(),
        "source_url": None,
        "is_demo": True,
    }
    payload.update(overrides)
    return payload


def test_inverted_validity_window_is_rejected(client):
    now = datetime.now(timezone.utc)
    response = client.post(
        "/api/v1/admin/import",
        json=_payload(
            "inverted-window",
            valid_from=(now + timedelta(hours=2)).isoformat(),
            valid_until=(now + timedelta(hours=1)).isoformat(),
        ),
    )
    assert response.status_code == 422


def test_missing_validity_window_never_appears_as_current(client):
    created = client.post(
        "/api/v1/admin/import",
        json=_payload("missing-validity", valid_from=None, valid_until=None),
    )
    assert created.status_code == 201
    assert created.json()["is_current"] is False
    current_only = client.get("/api/v1/advisories")
    assert all(row["source_record_id"] != "missing-validity" for row in current_only.json())

    all_records = client.get("/api/v1/advisories", params={"include_expired": True})
    record = next(row for row in all_records.json() if row["source_record_id"] == "missing-validity")
    assert record["is_current"] is False


def test_expired_record_is_not_current(client):
    now = datetime.now(timezone.utc)
    created = client.post(
        "/api/v1/admin/import",
        json=_payload(
            "expired-record",
            valid_from=(now - timedelta(hours=3)).isoformat(),
            valid_until=(now - timedelta(hours=1)).isoformat(),
        ),
    )
    assert created.status_code == 201
    assert created.json()["is_current"] is False
    current_only = client.get("/api/v1/advisories")
    assert all(row["source_record_id"] != "expired-record" for row in current_only.json())


def test_future_start_record_is_not_current(client):
    now = datetime.now(timezone.utc)
    created = client.post(
        "/api/v1/admin/import",
        json=_payload(
            "future-start",
            valid_from=(now + timedelta(hours=1)).isoformat(),
            valid_until=(now + timedelta(hours=3)).isoformat(),
        ),
    )
    assert created.status_code == 201
    assert created.json()["is_current"] is False
    current_only = client.get("/api/v1/advisories")
    assert all(row["source_record_id"] != "future-start" for row in current_only.json())
