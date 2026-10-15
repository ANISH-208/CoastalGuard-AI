from datetime import datetime, timezone, timedelta

def payload(record_id="record-1", **overrides):
    now = datetime.now(timezone.utc)
    data = {
        "source_name": "TEST_SOURCE",
        "source_record_id": record_id,
        "title": "DEMO ONLY — NOT A REAL WARNING",
        "original_text": "Synthetic test content. Not a real marine warning.",
        "region": "TEST_REGION",
        "issued_at": now.isoformat(),
        "valid_from": (now - timedelta(minutes=1)).isoformat(),
        "valid_until": (now + timedelta(hours=1)).isoformat(),
        "source_url": None,
        "is_demo": True,
    }
    data.update(overrides)
    return data

def test_expired_record_is_not_returned_by_default(client):
    now = datetime.now(timezone.utc)
    response = client.post("/api/v1/admin/import", json=payload(
        "expired-1",
        valid_from=(now - timedelta(days=2)).isoformat(),
        valid_until=(now - timedelta(days=1)).isoformat(),
    ))
    assert response.status_code == 201
    assert response.json()["is_current"] is False
    default_rows = client.get("/api/v1/advisories").json()
    assert all(row["source_record_id"] != "expired-1" for row in default_rows)
    all_rows = client.get("/api/v1/advisories?include_expired=true").json()
    assert any(row["source_record_id"] == "expired-1" for row in all_rows)

def test_missing_validity_is_not_current(client):
    response = client.post("/api/v1/admin/import", json=payload(
        "missing-validity", valid_from=None, valid_until=None
    ))
    assert response.status_code == 201
    assert response.json()["is_current"] is False
    rows = client.get("/api/v1/advisories?include_expired=true").json()
    row = next(x for x in rows if x["source_record_id"] == "missing-validity")
    assert row["is_current"] is False

def test_duplicate_source_record_is_rejected(client):
    first = client.post("/api/v1/admin/import", json=payload("same-id"))
    second = client.post("/api/v1/admin/import", json=payload("same-id"))
    assert first.status_code == 201
    assert second.status_code == 409

def test_unavailable_source_is_visible_in_status(client):
    response = client.post(
        "/api/v1/admin/sources/unavailable",
        params={"source_name": "TEST_UNAVAILABLE", "reason": "Synthetic test failure"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["last_error"] == "Synthetic test failure"
    status = client.get("/api/v1/sources/status")
    row = next(x for x in status.json() if x["source_name"] == "TEST_UNAVAILABLE")
    assert row["status"] == "unavailable"

def test_invalid_validity_window_rejected(client):
    now = datetime.now(timezone.utc)
    response = client.post("/api/v1/admin/import", json=payload(
        "bad-window", valid_from=now.isoformat(),
        valid_until=(now - timedelta(minutes=1)).isoformat(),
    ))
    assert response.status_code == 422

def test_health_does_not_claim_live_sources(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["live_official_sources_configured"] is False


def test_failed_source_prevents_advisory_from_being_current(client):
    imported = client.post("/api/v1/admin/import", json=payload("failed-source-record"))
    assert imported.status_code == 201
    assert imported.json()["is_current"] is True

    failed = client.post(
        "/api/v1/admin/sources/unavailable",
        params={"source_name": "TEST_SOURCE", "reason": "Synthetic connection failure"},
    )
    assert failed.status_code == 200
    rows = client.get("/api/v1/advisories?include_expired=true").json()
    row = next(x for x in rows if x["source_record_id"] == "failed-source-record")
    assert row["is_current"] is False


def test_operations_health_reports_failed_source_and_no_current_advisory(client):
    client.post("/api/v1/admin/import", json=payload("health-record"))
    client.post(
        "/api/v1/admin/sources/unavailable",
        params={"source_name": "TEST_SOURCE", "reason": "Synthetic failure"},
    )
    report = client.get("/api/v1/operations/health")
    assert report.status_code == 200
    data = report.json()
    assert data["overall"] == "attention_required"
    assert data["source_counts"]["failed"] == 1
    assert data["current_advisory_count"] == 0


def test_source_status_includes_freshness_classification(client):
    client.post(
        "/api/v1/admin/sources/unavailable",
        params={"source_name": "TEST_UNAVAILABLE", "reason": "Synthetic failure"},
    )
    rows = client.get("/api/v1/sources/status").json()
    row = next(x for x in rows if x["source_name"] == "TEST_UNAVAILABLE")
    assert row["freshness"] == "failed"


def test_import_runs_endpoint_returns_audit_metadata_only(client):
    from app.database import get_db
    from app.models import ImportRun

    db_gen = app_db = None
    # Use the same overridden database session fixture through dependency override.
    session_factory = client.app.dependency_overrides[get_db]
    generator = session_factory()
    db = next(generator)
    try:
        db.add(ImportRun(
            source_name="SYNTHETIC_TEST", mode="dry_run", outcome="previewed",
            input_count=3, accepted_count=2, rejected_count=1,
            imported_count=0, duplicates_skipped=0,
            error_summary=None,
        ))
        db.commit()
    finally:
        try:
            next(generator)
        except StopIteration:
            pass

    response = client.get("/api/v1/operations/import-runs")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["source_name"] == "SYNTHETIC_TEST"
    assert body[0]["outcome"] == "previewed"
    assert body[0]["input_count"] == 3
    assert "original_text" not in body[0]


def test_naive_timestamp_is_rejected(client):
    naive = datetime.now().replace(tzinfo=None).isoformat()
    response = client.post("/api/v1/admin/import", json=payload("naive-time", issued_at=naive))
    assert response.status_code == 422


def test_noncurrent_advisory_explains_gate_and_unverified_source(client):
    response = client.post("/api/v1/admin/import", json=payload(
        "missing-window", valid_from=None, valid_until=None,
    ))
    assert response.status_code == 201
    row = next(item for item in client.get("/api/v1/advisories?include_expired=true").json()
               if item["source_record_id"] == "missing-window")
    assert row["is_current"] is False
    assert row["current_reason"] == "Validity window is incomplete."
    assert row["source_verified"] is False
