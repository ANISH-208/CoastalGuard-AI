"""Create the first explicit CoastGuard AI schema.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, MetaData, String, Table, Text, UniqueConstraint, false, inspect

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _create_tables(bind):
    metadata = MetaData()
    Table("advisories", metadata,
        Column("id", Integer, primary_key=True),
        Column("source_name", String(100), nullable=False),
        Column("source_record_id", String(200), nullable=False),
        Column("title", String(300), nullable=True),
        Column("original_text", Text, nullable=False),
        Column("region", String(200), nullable=False),
        Column("issued_at", DateTime(timezone=True)),
        Column("valid_from", DateTime(timezone=True)),
        Column("valid_until", DateTime(timezone=True)),
        Column("retrieved_at", DateTime(timezone=True), nullable=False),
        Column("source_url", String(1000)),
        Column("is_demo", Boolean, nullable=False, server_default=false()),
        UniqueConstraint("source_name", "source_record_id", name="uq_advisory_source_record"),
    )
    Index("ix_advisories_id", metadata.tables["advisories"].c.id)
    Index("ix_advisories_source_name", metadata.tables["advisories"].c.source_name)
    Index("ix_advisories_region", metadata.tables["advisories"].c.region)
    Index("ix_advisories_valid_until", metadata.tables["advisories"].c.valid_until)
    Table("source_status", metadata,
        Column("id", Integer, primary_key=True),
        Column("source_name", String(100), nullable=False, unique=True),
        Column("status", String(30), nullable=False, server_default="unknown"),
        Column("last_attempt_at", DateTime(timezone=True)),
        Column("last_success_at", DateTime(timezone=True)),
        Column("last_error", Text), Column("notes", Text),
        Column("is_demo", Boolean, nullable=False, server_default=false()),
    )
    Index("ix_source_status_source_name", metadata.tables["source_status"].c.source_name, unique=True)
    Table("import_runs", metadata,
        Column("id", Integer, primary_key=True),
        Column("source_name", String(100), nullable=False),
        Column("mode", String(30), nullable=False),
        Column("outcome", String(30), nullable=False),
        Column("started_at", DateTime(timezone=True), nullable=False),
        Column("finished_at", DateTime(timezone=True), nullable=False),
        Column("input_count", Integer, nullable=False, server_default="0"),
        Column("accepted_count", Integer, nullable=False, server_default="0"),
        Column("rejected_count", Integer, nullable=False, server_default="0"),
        Column("imported_count", Integer, nullable=False, server_default="0"),
        Column("duplicates_skipped", Integer, nullable=False, server_default="0"),
        Column("error_summary", String(500)),
    )
    Index("ix_import_runs_id", metadata.tables["import_runs"].c.id)
    Index("ix_import_runs_source_name", metadata.tables["import_runs"].c.source_name)
    metadata.create_all(bind)
    # SQLite treats integer primary keys as rowids and omits their explicit
    # indexes from CREATE TABLE metadata, so create the model indexes directly.
    for table, name, column, unique in (
        ("advisories", "ix_advisories_id", "id", False),
        ("advisories", "ix_advisories_source_name", "source_name", False),
        ("source_status", "ix_source_status_source_name", "source_name", True),
        ("import_runs", "ix_import_runs_id", "id", False),
        ("import_runs", "ix_import_runs_source_name", "source_name", False),
    ):
        existing = {item["name"] for item in inspect(bind).get_indexes(table)}
        if name not in existing:
            op.create_index(name, table, [column], unique=unique)


def upgrade() -> None:
    bind = op.get_bind()
    # A pre-Alembic milestone database is converted by 0002. Leave its legacy
    # tables intact here so that the data migration can copy them deliberately.
    if "advisories" not in inspect(bind).get_table_names():
        _create_tables(bind)


def downgrade() -> None:
    bind = op.get_bind()
    for name in ("import_runs", "source_status", "advisories"):
        if name in inspect(bind).get_table_names():
            op.drop_table(name)
