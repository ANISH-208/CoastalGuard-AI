"""Convert pre-consolidation tables into the current schema.

Revision ID: 0002_legacy
Revises: 0001_initial
"""
from alembic import op
from sqlalchemy import inspect, text
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

revision = "0002_legacy"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _create_current(bind):
    path = Path(__file__).with_name("0001_initial_schema.py")
    spec = spec_from_file_location("coastguard_initial_migration", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    module._create_tables(bind)


def upgrade() -> None:
    bind = op.get_bind()
    names = set(inspect(bind).get_table_names())
    cols = {c["name"] for c in inspect(bind).get_columns("advisories")} if "advisories" in names else set()
    if "source" not in cols or "source_name" in cols:
        return
    # Remove old explicitly named indexes first; SQLite/PostgreSQL retain index
    # names when tables are renamed, which would collide with the new schema.
    for name in ("advisories", "sources", "import_runs"):
        if name in names:
            for index in inspect(bind).get_indexes(name):
                op.drop_index(index["name"], table_name=name)
    # Rename old tables so the new canonical names can be created safely.
    for name in ("advisories", "sources", "import_runs"):
        if name in names:
            op.rename_table(name, f"legacy_{name}")
    _create_current(bind)
    legacy = set(inspect(bind).get_table_names())
    if "legacy_advisories" in legacy:
        bind.execute(text("""
          INSERT INTO advisories
            (id, source_name, source_record_id, title, original_text, region, issued_at,
             valid_from, valid_until, retrieved_at, source_url, is_demo)
          SELECT id, source, source_id, title, original_text, region, issued_at,
                 valid_from, valid_until, retrieved_at, source_url, is_demo
          FROM legacy_advisories
        """))
    if "legacy_sources" in legacy:
        old_cols = {c["name"] for c in inspect(bind).get_columns("legacy_sources")}
        success = "last_successful_import_at" if "last_successful_import_at" in old_cols else "NULL"
        msg = "message" if "message" in old_cols else "NULL"
        bind.execute(text(f"""
          INSERT INTO source_status (source_name,status,last_attempt_at,last_success_at,last_error,notes,is_demo)
          SELECT name, status, last_attempt_at, {success}, NULL, {msg}, 0 FROM legacy_sources
        """))
    if "legacy_import_runs" in legacy:
        old_cols = {c["name"] for c in inspect(bind).get_columns("legacy_import_runs")}
        # The legacy audit never contained source payload text or credentials.
        bind.execute(text("""
          INSERT INTO import_runs
            (id,source_name,mode,outcome,started_at,finished_at,input_count,accepted_count,
             rejected_count,imported_count,duplicates_skipped,error_summary)
          SELECT id, source_label, mode, outcome, started_at, finished_at,
                 accepted_count + rejected_count + duplicate_count,
                 accepted_count, rejected_count, committed_count, duplicate_count, NULL
          FROM legacy_import_runs
        """))
    for name in ("legacy_import_runs", "legacy_sources", "legacy_advisories"):
        if name in inspect(bind).get_table_names():
            op.drop_table(name)


def downgrade() -> None:
    # Data conversion is intentionally irreversible: downgrade cannot restore the
    # older schema without risking loss of fields or audit meanings.
    raise RuntimeError("Legacy data migration is irreversible; restore a database backup instead.")
