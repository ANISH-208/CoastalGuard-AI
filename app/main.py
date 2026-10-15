from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.fixtures import load_demo_fixtures
from app.models import Advisory, ImportRun, SourceStatus
from app.schemas import AdvisoryCreate, AdvisoryRead, SourceStatusRead
from app.services import advisory_current_reason, advisory_is_current, create_advisory, source_freshness
from app.security import require_admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Development convenience only. Production schemas must be managed with Alembic.
    if settings.app_env.lower() in {"development", "test"}:
        Base.metadata.create_all(bind=engine)
    if settings.load_demo_fixtures and settings.app_env.lower() != "production":
        with SessionLocal() as db:
            load_demo_fixtures(db)
    yield

app = FastAPI(
    title="CoastGuard AI API",
    version="0.1.0",
    description="CoastGuard AI prototype. Fixtures are synthetic, not real warnings. Not fishing or navigation advice.",
    lifespan=lifespan,
)

# Local frontend development only. Replace with explicit trusted origins before deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

@app.get("/health")
def health():
    """Liveness probe: the process is running; does not imply DB/source health."""
    return {"status": "ok", "mode": settings.app_env, "live_official_sources_configured": False}

@app.get("/ready")
def readiness(db: Session = Depends(get_db)):
    """Readiness probe: returns 503 if the configured database is unreachable."""
    from fastapi import Response
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        # Do not leak database URLs, credentials, or driver errors to clients.
        raise HTTPException(status_code=503, detail="database_unavailable") from exc
    return {"status": "ready", "database": "reachable", "mode": settings.app_env}

@app.get("/api/v1/advisories", response_model=list[AdvisoryRead])
def list_advisories(
    region: str | None = Query(default=None, max_length=200),
    include_expired: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    statement = select(Advisory).order_by(Advisory.issued_at.desc(), Advisory.id.desc())
    if region:
        statement = statement.where(Advisory.region == region)
    rows = list(db.scalars(statement.limit(500)).all())
    now = datetime.now(timezone.utc)
    statuses = {item.source_name: item for item in db.scalars(select(SourceStatus)).all()}
    result = []
    for row in rows:
        current = advisory_is_current(row, now, statuses.get(row.source_name))
        if not include_expired and not current:
            continue
        item = AdvisoryRead.model_validate({**row.__dict__, "is_current": current, "current_reason": advisory_current_reason(row, now, statuses.get(row.source_name)), "source_verified": False})
        result.append(item)
        if len(result) >= limit:
            break
    return result

@app.get("/api/v1/sources/status", response_model=list[SourceStatusRead])
def source_status(db: Session = Depends(get_db)):
    rows = list(db.scalars(select(SourceStatus).order_by(SourceStatus.source_name)).all())
    now = datetime.now(timezone.utc)
    return [
        {
            "source_name": row.source_name,
            "status": row.status,
            "freshness": source_freshness(row, now),
            "last_attempt_at": row.last_attempt_at,
            "last_success_at": row.last_success_at,
            "last_error": row.last_error,
            "notes": row.notes,
            "is_demo": row.is_demo,
        }
        for row in rows
    ]

@app.get("/api/v1/operations/health")
def operations_health(db: Session = Depends(get_db)):
    """Operational snapshot; this endpoint does not poll any external source."""
    now = datetime.now(timezone.utc)
    statuses = list(db.scalars(select(SourceStatus).order_by(SourceStatus.source_name)).all())
    advisories = list(db.scalars(select(Advisory)).all())
    status_by_source = {item.source_name: item for item in statuses}
    freshness_counts = {"healthy": 0, "stale": 0, "failed": 0, "unknown": 0}
    source_rows = []
    for item in statuses:
        freshness = source_freshness(item, now)
        freshness_counts[freshness] += 1
        source_rows.append({
            "source_name": item.source_name,
            "freshness": freshness,
            "last_attempt_at": item.last_attempt_at,
            "last_success_at": item.last_success_at,
            "has_error": bool(item.last_error),
            "is_demo": item.is_demo,
        })
    current_count = sum(
        advisory_is_current(item, now, status_by_source.get(item.source_name))
        for item in advisories
    )
    return {
        "checked_at": now,
        "overall": "attention_required" if not statuses or any(freshness_counts[k] for k in ("stale", "failed", "unknown")) else "ok",
        "freshness_threshold_hours": settings.source_stale_after_hours,
        "advisory_max_age_hours": settings.advisory_max_age_hours,
        "source_counts": freshness_counts,
        "source_count": len(statuses),
        "advisory_count": len(advisories),
        "current_advisory_count": current_count,
        "sources": source_rows,
        "note": "Status snapshot only; no live source polling occurs here. Unknown, stale, or failed sources do not qualify advisories as current.",
    }

@app.get("/api/v1/operations/pilot-readiness")
def pilot_readiness(db: Session = Depends(get_db)):
    """Report pilot prerequisites without treating software checks as safety approval."""
    now = datetime.now(timezone.utc)
    source_rows = list(db.scalars(select(SourceStatus)).all())
    advisory_rows = list(db.scalars(select(Advisory)).all())
    status_by_source = {item.source_name: item for item in source_rows}
    freshness = [source_freshness(item, now) for item in source_rows]
    demo_advisories = sum(bool(item.is_demo) for item in advisory_rows)
    demo_sources = sum(bool(item.is_demo) for item in source_rows)
    current_records = sum(
        advisory_is_current(item, now, status_by_source.get(item.source_name))
        for item in advisory_rows
    )

    # These three gates intentionally remain false until a human-reviewed process
    # and an approved, verified live source are implemented and evidenced.
    checks = {
        "official_source_access_and_schema_verified": False,
        "community_review_completed": False,
        "field_validation_completed": False,
        "admin_token_configured": bool(settings.admin_api_token),
        "non_demo_source_records_present": bool(source_rows) and demo_sources == 0,
        "no_demo_advisories_present": demo_advisories == 0,
        "all_sources_healthy": bool(source_rows) and all(value == "healthy" for value in freshness),
        "at_least_one_record_passes_current_checks": current_records > 0,
    }
    blockers = [key for key, passed in checks.items() if not passed]
    return {
        "readiness": "blocked" if blockers else "review_required",
        "checks": checks,
        "blockers": blockers,
        "counts": {
            "sources": len(source_rows),
            "demo_sources": demo_sources,
            "advisories": len(advisory_rows),
            "demo_advisories": demo_advisories,
            "records_passing_current_checks": current_records,
        },
        "checked_at": now,
        "safety_notice": (
            "This diagnostic is not a safety certification. A record passing software checks is not proof "
            "that an official warning is authentic, complete, or safe to rely on. Human review and official "
            "source verification are required before any field pilot."
        ),
    }


@app.get("/api/v1/operations/import-runs")
def import_runs(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db), _admin: str = Depends(require_admin)):
    """Read-only import audit metadata; payload text and credentials are never stored here."""
    rows = db.scalars(select(ImportRun).order_by(ImportRun.id.desc()).limit(limit)).all()
    return [
        {
            "id": row.id, "source_name": row.source_name, "mode": row.mode,
            "outcome": row.outcome, "started_at": row.started_at,
            "finished_at": row.finished_at, "input_count": row.input_count,
            "accepted_count": row.accepted_count, "rejected_count": row.rejected_count,
            "imported_count": row.imported_count, "duplicates_skipped": row.duplicates_skipped,
            "error_summary": row.error_summary,
        }
        for row in rows
    ]

@app.post("/api/v1/admin/import", response_model=AdvisoryRead, status_code=201)
def import_advisory(payload: AdvisoryCreate, db: Session = Depends(get_db), _admin: str = Depends(require_admin)):
    # Protected by the administrative bearer-token dependency; still use HTTPS in deployment.
    try:
        row = create_advisory(db, payload, commit=False)
        now = datetime.now(timezone.utc)
        db.add(ImportRun(
            source_name=payload.source_name, mode="admin_api", outcome="committed",
            started_at=now, finished_at=now, input_count=1, accepted_count=1,
            rejected_count=0, imported_count=1, duplicates_skipped=0,
        ))
        db.commit()
        db.refresh(row)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate source record") from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Import transaction failed") from exc
    status = db.scalar(select(SourceStatus).where(SourceStatus.source_name == row.source_name))
    result = AdvisoryRead.model_validate({**row.__dict__, "is_current": advisory_is_current(row, source_status=status), "current_reason": advisory_current_reason(row, source_status=status), "source_verified": False})
    return result

@app.post("/api/v1/admin/sources/unavailable", response_model=SourceStatusRead)
def mark_source_unavailable(
    source_name: str = Query(min_length=1, max_length=100),
    reason: str = Query(min_length=1, max_length=500),
    db: Session = Depends(get_db),
    _admin: str = Depends(require_admin),
):
    # Protected by the administrative bearer-token dependency.
    row = db.scalar(select(SourceStatus).where(SourceStatus.source_name == source_name))
    now = datetime.now(timezone.utc)
    if row is None:
        row = SourceStatus(
            source_name=source_name, status="unavailable", last_attempt_at=now,
            last_success_at=None, last_error=reason,
            notes="Marked unavailable by local admin/test helper.", is_demo=True,
        )
        db.add(row)
    else:
        row.status = "unavailable"
        row.last_attempt_at = now
        row.last_error = reason
    db.commit()
    db.refresh(row)
    return row
