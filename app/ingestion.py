from pathlib import Path
import json
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Advisory
from app.schemas import AdvisoryCreate
from app.services import create_advisory


class BulletinImportError(ValueError):
    pass


def load_bulletin_file(path: str | Path) -> list[dict[str, Any]]:
    """Read a JSON object or array of bulletin records from a local file.

    This function does not fetch remote data and does not verify source permissions.
    The operator is responsible for confirming that the content may be imported.
    """
    file_path = Path(path)
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BulletinImportError(f"Cannot read input file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BulletinImportError(f"Input is not valid JSON: {exc}") from exc

    if isinstance(payload, dict):
        records = payload.get("records")
        if records is None:
            records = [payload]
    elif isinstance(payload, list):
        records = payload
    else:
        raise BulletinImportError("JSON root must be an object or an array of objects")

    if not records or not all(isinstance(record, dict) for record in records):
        raise BulletinImportError("Expected one or more JSON objects representing records")
    return records


def import_bulletin_records(db: Session, records: list[dict[str, Any]]) -> dict[str, int]:
    """Validate and import records, skipping duplicate source identifiers.

    This is a manual-import pipeline. It does not claim records are live or official.
    """
    counts = {"imported": 0, "duplicates_skipped": 0, "invalid": 0}
    for index, raw in enumerate(records):
        try:
            payload = AdvisoryCreate.model_validate(raw)
        except ValidationError as exc:
            counts["invalid"] += 1
            continue

        existing = db.scalar(
            select(Advisory).where(
                Advisory.source_name == payload.source_name,
                Advisory.source_record_id == payload.source_record_id,
            )
        )
        if existing is not None:
            counts["duplicates_skipped"] += 1
            continue

        try:
            create_advisory(db, payload)
        except ValueError:
            counts["duplicates_skipped"] += 1
        else:
            counts["imported"] += 1
    return counts
