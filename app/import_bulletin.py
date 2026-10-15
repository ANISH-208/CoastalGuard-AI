import argparse
import sys

from app.database import Base, SessionLocal, engine
from app.ingestion import BulletinImportError, import_bulletin_records, load_bulletin_file


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Import locally supplied bulletin JSON. This command does not fetch remote data. "
            "Confirm source permissions before importing official content."
        )
    )
    parser.add_argument("json_file", help="Path to a JSON object or array of advisory records")
    args = parser.parse_args()

    try:
        records = load_bulletin_file(args.json_file)
    except BulletinImportError as exc:
        print(f"Import error: {exc}", file=sys.stderr)
        return 2

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        counts = import_bulletin_records(db, records)

    print(
        "Manual import complete: "
        f"{counts['imported']} imported, "
        f"{counts['duplicates_skipped']} duplicates skipped, "
        f"{counts['invalid']} invalid records."
    )
    if counts["invalid"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
