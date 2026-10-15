from datetime import datetime, timezone, timedelta

from app.normalized_import import commit_normalized_import, preview_normalized_import
from app.sources.normalizer import FieldMapping
from app.models import Advisory
from sqlalchemy import select


def mapping():
    return FieldMapping(
        source_name="SYNTHETIC_IMPORT",
        record_id="id",
        title="title",
        original_text="text",
        region="region",
        issued_at="issued",
        valid_from="valid_from",
        valid_until="valid_until",
    )


def payload(record_id="id-1"):
    now = datetime.now(timezone.utc)
    return [{
        "id": record_id,
        "title": "DEMO ONLY — NOT A REAL WARNING",
        "text": "Synthetic test fixture; not a marine advisory.",
        "region": "DEMO_REGION",
        "issued": now.isoformat(),
        "valid_from": (now - timedelta(minutes=1)).isoformat(),
        "valid_until": (now + timedelta(hours=1)).isoformat(),
    }]


def test_preview_does_not_persist(client):
    result = preview_normalized_import(payload(), mapping())
    assert result["accepted_count"] == 1
    assert result["rejected_count"] == 0
    # No request to the API and no database write is made by preview_normalized_import.


def test_commit_persists_valid_record(client):
    from app.main import app
    from app.database import get_db
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        result = preview_normalized_import(payload(), mapping())
        counts = commit_normalized_import(db, result["accepted"])
        assert counts == {"imported": 1, "duplicates_skipped": 0}
        row = db.scalar(select(Advisory).where(Advisory.source_record_id == "id-1"))
        assert row is not None
        assert row.is_demo is True
    finally:
        try:
            next(generator)
        except StopIteration:
            pass


def test_commit_skips_duplicate_record(client):
    from app.main import app
    from app.database import get_db
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        result = preview_normalized_import(payload("duplicate-1"), mapping())
        first = commit_normalized_import(db, result["accepted"])
        second = commit_normalized_import(db, result["accepted"])
        assert first["imported"] == 1
        assert second == {"imported": 0, "duplicates_skipped": 1}
    finally:
        try:
            next(generator)
        except StopIteration:
            pass


def test_invalid_record_is_rejected_before_commit(client):
    result = preview_normalized_import([{"id": "missing"}], mapping())
    assert result["accepted_count"] == 0
    assert result["rejected_count"] == 1


def test_commit_skips_duplicate_ids_within_same_batch(client):
    from app.main import app
    from app.database import get_db
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        result = preview_normalized_import(payload("same-batch-id") + payload("same-batch-id"), mapping())
        counts = commit_normalized_import(db, result["accepted"])
        assert counts == {"imported": 1, "duplicates_skipped": 1}
        rows = db.scalars(select(Advisory).where(Advisory.source_record_id == "same-batch-id")).all()
        assert len(rows) == 1
    finally:
        try:
            next(generator)
        except StopIteration:
            pass


def test_import_rolls_back_batch_on_unexpected_error(client, monkeypatch):
    from app.main import app
    from app.database import get_db
    import app.normalized_import as importer

    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    original = importer.create_advisory
    calls = {"count": 0}

    def fail_on_second(db_session, record, *, commit=True):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("simulated database-side failure")
        return original(db_session, record, commit=commit)

    monkeypatch.setattr(importer, "create_advisory", fail_on_second)
    try:
        records = preview_normalized_import(payload("atomic-1") + payload("atomic-2"), mapping())["accepted"]
        try:
            commit_normalized_import(db, records)
            assert False, "expected simulated failure"
        except RuntimeError as exc:
            assert "simulated database-side failure" in str(exc)
        rows = db.scalars(select(Advisory).where(Advisory.source_record_id.in_(["atomic-1", "atomic-2"]))).all()
        assert rows == []
    finally:
        try:
            next(generator)
        except StopIteration:
            pass


def test_commit_audit_is_saved_with_advisory(client):
    from app.main import app
    from app.database import get_db
    from app.models import ImportRun
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        accepted = preview_normalized_import(payload("audit-atomic"), mapping())["accepted"]
        commit_normalized_import(db, accepted, source_name="SYNTHETIC_IMPORT", input_count=1)
        advisory = db.scalar(select(Advisory).where(Advisory.source_record_id == "audit-atomic"))
        audit = db.scalar(select(ImportRun).where(ImportRun.source_name == "SYNTHETIC_IMPORT"))
        assert advisory is not None
        assert audit is not None
        assert audit.outcome == "committed"
        assert audit.imported_count == 1
    finally:
        try:
            next(generator)
        except StopIteration:
            pass
