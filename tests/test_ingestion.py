import json
from datetime import datetime, timezone, timedelta

from app.database import Base
from app.ingestion import BulletinImportError, import_bulletin_records, load_bulletin_file
from app.models import Advisory


def record(record_id="import-1"):
    now = datetime.now(timezone.utc)
    return {
        "source_name": "MANUAL_TEST",
        "source_record_id": record_id,
        "title": "DEMO ONLY — NOT A REAL WARNING",
        "original_text": "Synthetic test fixture only.",
        "region": "TEST_REGION",
        "issued_at": now.isoformat(),
        "valid_from": (now - timedelta(minutes=1)).isoformat(),
        "valid_until": (now + timedelta(hours=1)).isoformat(),
        "source_url": None,
        "is_demo": True,
    }


def test_import_pipeline_skips_duplicate_and_counts_invalid(client):
    # Reuse the isolated test database by writing through the endpoint first.
    first = client.post("/api/v1/admin/import", json=record("duplicate-id"))
    assert first.status_code == 201

    from app.main import app
    from app.database import get_db
    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        counts = import_bulletin_records(db, [record("duplicate-id"), record("new-id"), {"bad": "record"}])
        assert counts == {"imported": 1, "duplicates_skipped": 1, "invalid": 1}
    finally:
        try:
            next(db_generator)
        except StopIteration:
            pass


def test_load_bulletin_file_reads_json_object(tmp_path):
    path = tmp_path / "one.json"
    path.write_text(json.dumps(record()), encoding="utf-8")
    result = load_bulletin_file(path)
    assert len(result) == 1
    assert result[0]["source_record_id"] == "import-1"


def test_load_bulletin_file_rejects_invalid_json(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    try:
        load_bulletin_file(path)
        assert False, "Expected BulletinImportError"
    except BulletinImportError:
        pass
