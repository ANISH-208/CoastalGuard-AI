from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from app.schemas import AdvisoryCreate
from app.config import settings


@dataclass(frozen=True)
class FieldMapping:
    """Explicit mapping from source JSON keys to CoastGuard advisory fields.

    Keys must be configured only after the official source schema is reviewed.
    No source-specific key names or meanings are guessed by this module.
    """
    source_name: str
    record_id: str
    title: str
    original_text: str
    region: str
    issued_at: str | None = None
    valid_from: str | None = None
    valid_until: str | None = None
    source_url: str | None = None


@dataclass
class NormalizationResult:
    records: list[AdvisoryCreate]
    rejected: list[dict[str, Any]]


def _read_path(item: Any, path: str | None) -> Any:
    if not path:
        return None
    value = item
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _to_datetime(value: Any) -> Any:
    # Pydantic parses ISO strings and datetime values. Do not guess numeric epochs
    # or locale-specific date formats without a documented source contract.
    if value is None or isinstance(value, (str, datetime)):
        return value
    raise ValueError("Timestamp must be an ISO-8601 string or datetime; numeric/unknown formats are not inferred")


def normalize_payload(
    payload: Any,
    mapping: FieldMapping,
    *,
    source_url_fallback: str | None = None,
    is_demo: bool = True,
) -> NormalizationResult:
    """Normalize only fields explicitly mapped by a reviewed source schema.

    Accepts a list, a single object, or an object containing a `data` array.
    The caller must verify the official schema and permitted reuse first.
    """
    if isinstance(payload, list):
        raw_records = payload
    elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
        raw_records = payload["data"]
    elif isinstance(payload, dict) and isinstance(payload.get("records"), list):
        raw_records = payload["records"]
    elif isinstance(payload, dict):
        raw_records = [payload]
    else:
        raise ValueError("Expected a JSON object or array")

    if len(raw_records) > settings.max_import_records:
        raise ValueError(f"Record limit exceeded (maximum {settings.max_import_records})")

    accepted: list[AdvisoryCreate] = []
    rejected: list[dict[str, Any]] = []

    for index, raw in enumerate(raw_records):
        if not isinstance(raw, dict):
            rejected.append({"index": index, "reason": "Record is not a JSON object"})
            continue
        try:
            record = {
                "source_name": mapping.source_name,
                "source_record_id": _read_path(raw, mapping.record_id),
                "title": _read_path(raw, mapping.title),
                "original_text": _read_path(raw, mapping.original_text),
                "region": _read_path(raw, mapping.region),
                "issued_at": _to_datetime(_read_path(raw, mapping.issued_at)),
                "valid_from": _to_datetime(_read_path(raw, mapping.valid_from)),
                "valid_until": _to_datetime(_read_path(raw, mapping.valid_until)),
                "source_url": _read_path(raw, mapping.source_url) or source_url_fallback,
                "is_demo": is_demo,
            }
            advisory = AdvisoryCreate.model_validate(record)
        except (ValidationError, ValueError, TypeError) as exc:
            # Keep rejection reason, but do not echo full source text into logs.
            reason = str(exc).splitlines()[0][:300]
            rejected.append({"index": index, "reason": reason})
            continue
        accepted.append(advisory)

    return NormalizationResult(records=accepted, rejected=rejected)
