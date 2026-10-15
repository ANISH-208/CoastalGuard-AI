"""Safe dry-run and transactional commit helpers for reviewed local imports."""
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Advisory, ImportRun
from app.services import create_advisory
from app.sources.normalizer import FieldMapping, normalize_payload


def preview_normalized_import(payload: Any, mapping: FieldMapping) -> dict[str, Any]:
    result = normalize_payload(payload, mapping)
    return {
        "accepted": result.records,
        "rejected": result.rejected,
        "accepted_count": len(result.records),
        "rejected_count": len(result.rejected),
    }


def commit_normalized_import(
    db: Session,
    records,
    *,
    source_name: str | None = None,
    input_count: int | None = None,
    rejected_count: int = 0,
    allow_partial: bool = False,
) -> dict[str, int]:
    """Commit advisory rows, source status, and audit metadata atomically."""
    counts = {"imported": 0, "duplicates_skipped": 0}
    started_at = datetime.now(timezone.utc)
    try:
        for payload in records:
            existing = db.scalar(select(Advisory).where(
                Advisory.source_name == payload.source_name,
                Advisory.source_record_id == payload.source_record_id,
            ))
            if existing is not None:
                counts["duplicates_skipped"] += 1
                continue
            create_advisory(db, payload, commit=False)
            counts["imported"] += 1
        if source_name is not None:
            now = datetime.now(timezone.utc)
            db.add(ImportRun(
                source_name=source_name, mode="commit",
                outcome="committed_partial" if rejected_count else "committed",
                started_at=started_at, finished_at=now,
                input_count=input_count if input_count is not None else len(records) + rejected_count,
                accepted_count=len(records), rejected_count=rejected_count,
                imported_count=counts["imported"],
                duplicates_skipped=counts["duplicates_skipped"],
                error_summary="Partial import explicitly allowed." if rejected_count and allow_partial else None,
            ))
        db.commit()
        return counts
    except Exception:
        db.rollback()
        raise
