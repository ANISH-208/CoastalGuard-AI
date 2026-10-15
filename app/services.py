from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Advisory, SourceStatus
from app.config import settings
from app.schemas import AdvisoryCreate


def as_utc(value: datetime) -> datetime:
    # SQLite may return naive datetimes despite timezone=True.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def source_freshness(status: SourceStatus | None, now: datetime | None = None) -> str:
    """Classify source health conservatively; only a recent successful retrieval is healthy."""
    if status is None:
        return "unknown"
    if status.status in {"unavailable", "failed", "error"}:
        return "failed"
    if status.status in {"unknown", "disabled", "not_configured"}:
        return "unknown"
    if status.status == "stale":
        return "stale"
    if status.status not in {"manual_import", "healthy", "live", "demo_fixture"}:
        return "unknown"
    now = as_utc(now or datetime.now(timezone.utc))
    if status.last_success_at is None:
        return "unknown"
    age_hours = (now - as_utc(status.last_success_at)).total_seconds() / 3600
    if age_hours < 0:
        return "unknown"
    if age_hours > settings.source_stale_after_hours:
        return "stale"
    return "healthy"


def advisory_current_reason(
    advisory: Advisory,
    now: datetime | None = None,
    source_status: SourceStatus | None = None,
) -> str | None:
    """Return why the record cannot be displayed as current; None means checks pass."""
    now = as_utc(now or datetime.now(timezone.utc))
    if advisory.valid_from is None or advisory.valid_until is None:
        return "Validity window is incomplete."
    if as_utc(advisory.valid_until) <= as_utc(advisory.valid_from):
        return "Validity window is invalid."
    if as_utc(advisory.valid_from) > now:
        return "Validity period has not started."
    if as_utc(advisory.valid_until) <= now:
        return "Advisory validity period has expired."
    retrieved_at = getattr(advisory, "retrieved_at", None)
    if retrieved_at is None:
        return "Retrieval time is missing."
    age_hours = (now - as_utc(retrieved_at)).total_seconds() / 3600
    if age_hours < 0:
        return "Retrieval time is in the future."
    if age_hours > settings.advisory_max_age_hours:
        return "Retrieved advisory is stale."
    health = source_freshness(source_status, now)
    if health == "failed":
        return "Source is unavailable or has failed."
    if health == "stale":
        return "Source data is stale."
    if health == "unknown":
        return "Source health is unknown."
    last_success = source_status.last_success_at if source_status else None
    if last_success is None:
        return "Source has no recorded successful retrieval."
    success_age_hours = (now - as_utc(last_success)).total_seconds() / 3600
    if success_age_hours < 0:
        return "Source success time is in the future."
    if success_age_hours > settings.source_stale_after_hours:
        return "Source data is stale."
    return None


def advisory_is_current(
    advisory: Advisory,
    now: datetime | None = None,
    source_status: SourceStatus | None = None,
) -> bool:
    return advisory_current_reason(advisory, now, source_status) is None


def create_advisory(db: Session, payload: AdvisoryCreate, *, commit: bool = True) -> Advisory:
    """Create an advisory. Set commit=False when composing a larger transaction."""
    existing = db.scalar(select(Advisory).where(
        Advisory.source_name == payload.source_name,
        Advisory.source_record_id == payload.source_record_id,
    ))
    if existing:
        raise ValueError("An advisory with this source_name and source_record_id already exists")
    values = payload.model_dump()
    if values.get("source_url") is not None:
        values["source_url"] = str(values["source_url"])
    row = Advisory(**values, retrieved_at=datetime.now(timezone.utc))
    db.add(row)
    db.flush()
    status = db.scalar(select(SourceStatus).where(SourceStatus.source_name == payload.source_name))
    now = datetime.now(timezone.utc)
    if status is None:
        status = SourceStatus(
            source_name=payload.source_name, status="manual_import",
            last_attempt_at=now, last_success_at=now, last_error=None,
            notes="Manual import only; no live source polling is configured.",
            is_demo=payload.is_demo,
        )
        db.add(status)
    else:
        status.status = "manual_import"
        status.last_attempt_at = now
        status.last_success_at = now
        status.last_error = None
        status.is_demo = payload.is_demo
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row
