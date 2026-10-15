from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Advisory, SourceStatus

DEMO_SOURCE = "DEMO_FIXTURE"

def load_demo_fixtures(db: Session) -> None:
    # Synthetic fixtures only; these are not marine warnings.
    now = datetime.now(timezone.utc)
    records = [
        {
            "source_name": DEMO_SOURCE,
            "source_record_id": "synthetic-validity-window",
            "title": "DEMO ONLY — NOT A REAL WARNING",
            "original_text": "SYNTHETIC TEST DATA ONLY. Not a marine forecast, warning, or recommendation. Do not use for real-world decisions.",
            "region": "DEMO_REGION_NOT_REAL",
            "issued_at": now - timedelta(minutes=5),
            "valid_from": now - timedelta(minutes=1),
            "valid_until": now + timedelta(hours=1),
            "source_url": None, "is_demo": True,
        },
        {
            "source_name": DEMO_SOURCE,
            "source_record_id": "synthetic-expired-window",
            "title": "DEMO ONLY — EXPIRED TEST RECORD — NOT A REAL WARNING",
            "original_text": "SYNTHETIC EXPIRED TEST DATA ONLY. Not a marine forecast, warning, or recommendation.",
            "region": "DEMO_REGION_NOT_REAL",
            "issued_at": now - timedelta(days=2),
            "valid_from": now - timedelta(days=2),
            "valid_until": now - timedelta(days=1),
            "source_url": None, "is_demo": True,
        },
        {
            "source_name": DEMO_SOURCE,
            "source_record_id": "synthetic-missing-validity",
            "title": "DEMO ONLY — MISSING VALIDITY TEST — NOT A REAL WARNING",
            "original_text": "SYNTHETIC TEST DATA ONLY. Missing validity dates must never be treated as current.",
            "region": "DEMO_REGION_NOT_REAL",
            "issued_at": now, "valid_from": None, "valid_until": None,
            "source_url": None, "is_demo": True,
        },
    ]
    for item in records:
        existing = db.scalar(select(Advisory).where(
            Advisory.source_name == item["source_name"],
            Advisory.source_record_id == item["source_record_id"],
        ))
        if existing is None:
            db.add(Advisory(**item, retrieved_at=now))
    status = db.scalar(select(SourceStatus).where(SourceStatus.source_name == DEMO_SOURCE))
    if status is None:
        db.add(SourceStatus(
            source_name=DEMO_SOURCE, status="demo_fixture",
            last_attempt_at=now, last_success_at=now, last_error=None,
            notes="Synthetic local fixtures only. No external source was contacted.",
            is_demo=True,
        ))
    db.commit()
