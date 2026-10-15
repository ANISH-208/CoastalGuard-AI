import argparse
import json
import sys
from pathlib import Path

from app.database import SessionLocal
from app.config import settings
from app.models import ImportRun
from app.normalized_import import commit_normalized_import, preview_normalized_import
from app.sources.normalizer import FieldMapping


def count_input_records(payload) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return len(payload["data"])
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Review and optionally import a local JSON bulletin using explicit field mappings. "
            "Dry-run is the default; --commit is required to write records."
        )
    )
    parser.add_argument("json_file", help="Path to a local JSON object/array")
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--id-field", required=True)
    parser.add_argument("--title-field", required=True)
    parser.add_argument("--text-field", required=True)
    parser.add_argument("--region-field", required=True)
    parser.add_argument("--issued-field")
    parser.add_argument("--valid-from-field")
    parser.add_argument("--valid-until-field")
    parser.add_argument("--source-url-field")
    parser.add_argument("--commit", action="store_true", help="Persist accepted records after validation")
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Allow committing accepted records even if some source records were rejected",
    )
    parser.add_argument("--report", help="Optional path to write a local review report JSON")
    args = parser.parse_args()

    try:
        input_path = Path(args.json_file)
        if input_path.stat().st_size > settings.max_import_file_bytes:
            raise ValueError(f"Input file exceeds {settings.max_import_file_bytes} byte limit")
        with input_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Cannot read JSON input: {exc}", file=sys.stderr)
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
        preview = preview_normalized_import(payload, mapping)
    except ValueError as exc:
        print(f"Cannot normalize input: {exc}", file=sys.stderr)
        return 2

    report = {
        "mode": "commit_requested" if args.commit else "dry_run",
        "accepted_count": preview["accepted_count"],
        "rejected_count": preview["rejected_count"],
        "accepted_records": [
            record.model_dump(mode="json")
            for record in preview["accepted"]
        ],
        "rejected_records": preview["rejected"],
        "persisted": False,
        "note": "Review content and source permissions. Imported data is not independently verified by this tool.",
    }

    if args.report:
        Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps({
        "mode": report["mode"],
        "accepted_count": report["accepted_count"],
        "rejected_count": report["rejected_count"],
        "report_path": args.report,
        "persisted": False,
    }, indent=2))

    outcome = "previewed"
    counts = {"imported": 0, "duplicates_skipped": 0}
    error_summary = None
    if args.commit and preview["rejected_count"] and not args.allow_partial:
        outcome = "blocked"
        error_summary = "Commit blocked: one or more records were rejected."
        print(
            "Commit blocked because one or more records were rejected. Fix the input or "
            "explicitly use --allow-partial after reviewing the rejection report.",
            file=sys.stderr,
        )
    elif args.commit:
        try:
            with SessionLocal() as db:
                counts = commit_normalized_import(
                    db, preview["accepted"], source_name=args.source_name,
                    input_count=count_input_records(payload),
                    rejected_count=preview["rejected_count"], allow_partial=args.allow_partial,
                )
            outcome = "committed_partial" if preview["rejected_count"] else "committed"
        except Exception as exc:
            outcome = "failed"
            error_summary = f"Import transaction failed ({type(exc).__name__})."
            with SessionLocal() as db:
                db.add(ImportRun(
                    source_name=args.source_name, mode="commit", outcome="failed",
                    input_count=count_input_records(payload),
                    accepted_count=preview["accepted_count"],
                    rejected_count=preview["rejected_count"], imported_count=0,
                    duplicates_skipped=0, error_summary=error_summary,
                ))
                db.commit()
            print("Import failed; no advisory records were committed.", file=sys.stderr)
            return 2
        report["persisted"] = True
        report["commit_counts"] = counts
        if args.report:
            Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({"persisted": True, **counts}, indent=2))
    else:
        print("Dry run only: no advisory records were saved.")

    # Preview and blocked outcomes are metadata-only. Committed audit metadata is
    # inserted in the same transaction as its advisory records above.
    if not args.commit or outcome == "blocked":
        with SessionLocal() as db:
            db.add(ImportRun(
                source_name=args.source_name,
                mode="commit" if args.commit else "dry_run",
                outcome=outcome,
                input_count=count_input_records(payload),
                accepted_count=preview["accepted_count"],
                rejected_count=preview["rejected_count"],
                imported_count=0,
                duplicates_skipped=0,
                error_summary=error_summary,
            ))
            db.commit()

    if outcome == "blocked":
        return 1
    return 0 if preview["rejected_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
