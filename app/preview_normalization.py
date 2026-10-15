import argparse
import json
import os
import sys

from app.sources.imd import (
    IMDSourceConfig,
    SourceConfigurationError,
    SourceFetchError,
    fetch_imd_payload,
)
from app.sources.normalizer import FieldMapping, normalize_payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run normalization of a local JSON file, or optionally an approved IMD endpoint. "
            "This tool never saves records to the database."
        )
    )
    parser.add_argument("--file", help="Local JSON file containing source records")
    parser.add_argument("--source-name", required=True, help="Configured source label")
    parser.add_argument("--id-field", required=True, help="Reviewed source field path for unique record ID")
    parser.add_argument("--title-field", required=True, help="Reviewed source field path for title")
    parser.add_argument("--text-field", required=True, help="Reviewed source field path for original text")
    parser.add_argument("--region-field", required=True, help="Reviewed source field path for affected region")
    parser.add_argument("--issued-field", help="Reviewed source field path for issue time")
    parser.add_argument("--valid-from-field", help="Reviewed source field path for validity start")
    parser.add_argument("--valid-until-field", help="Reviewed source field path for validity end")
    parser.add_argument("--source-url-field", help="Reviewed source field path for source URL")
    parser.add_argument("--approved-live-fetch", action="store_true", help="Fetch configured endpoint; use only after access approval")
    args = parser.parse_args()

    if bool(args.file) == bool(args.approved_live_fetch):
        parser.error("Choose exactly one of --file or --approved-live-fetch")

    try:
        if args.file:
            with open(args.file, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        else:
            config = IMDSourceConfig(
                enabled=os.getenv("IMD_MARINE_ENABLED", "false").lower() == "true",
                endpoint_url=os.getenv("IMD_MARINE_ENDPOINT") or None,
                auth_header_name=os.getenv("IMD_AUTH_HEADER_NAME") or None,
                auth_header_value=os.getenv("IMD_AUTH_HEADER_VALUE") or None,
                timeout_seconds=float(os.getenv("IMD_TIMEOUT_SECONDS", "10")),
            )
            payload = fetch_imd_payload(config)
    except (OSError, json.JSONDecodeError, SourceConfigurationError, SourceFetchError) as exc:
        print(f"Cannot load source payload: {exc}", file=sys.stderr)
        return 2

    mapping = FieldMapping(
        source_name=args.source_name,
        record_id=args.id_field,
        title=args.title_field,
        original_text=args.text_field,
        region=args.region_field,
        issued_at=args.issued_field,
        valid_from=args.valid_from_field,
        valid_until=args.valid_until_field,
        source_url=args.source_url_field,
    )
    try:
        result = normalize_payload(payload, mapping)
    except ValueError as exc:
        print(f"Normalization failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({
        "accepted_count": len(result.records),
        "rejected_count": len(result.rejected),
        "accepted_preview": [
            record.model_dump(mode="json", exclude={"original_text"})
            for record in result.records[:3]
        ],
        "rejected": result.rejected,
        "saved_to_database": False,
        "note": "Dry run only. Confirm official field semantics, validity and reuse permissions before import.",
    }, indent=2))
    return 0 if not result.rejected else 1


if __name__ == "__main__":
    raise SystemExit(main())
