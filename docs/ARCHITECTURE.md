# Architecture and consolidated feature inventory

## Project shape

- `app/main.py`: FastAPI routes, liveness/readiness, advisory listing, source operations, pilot readiness, and protected admin routes.
- `app/config.py`, `app/security.py`: environment settings, import/freshness limits, and fail-closed shared bearer-token check.
- `app/schemas.py`, `app/services.py`: strict request validation, current-display reasons, freshness classification, and source-status updates.
- `app/sources/normalizer.py`: allowlisted field mapping from JSON to the app schema; rejects unsupported timestamp forms and bounds record counts.
- `app/import_normalized.py`, `app/normalized_import.py`: local dry-run/report/commit workflow; committed advisory, source-status, and audit rows share one transaction.
- `app/sources/imd.py`: disabled-by-default, HTTPS-only IMD request adapter. It does not write or publish fetched data.
- `frontend/`: React dashboard showing bulletin text, source, issue/validity/retrieval times, current-check reason, offline state, and an explicit unverified-source label.
- `alembic/`: explicit initial schema and a legacy-table conversion revision; migrations are versioned and do not derive DDL from live ORM metadata.
- `tests/`: synthetic unit, API, importer, security, readiness, and pilot workflow coverage.
- `Dockerfile`, `compose.yaml`, `.github/workflows/ci.yml`: containerized local deployment and CI backend, migration, and frontend checks.

## Feature progression included in the consolidated bundle

The cumulative project bundle contains the integrated outcomes developed across Milestones 1–15:

1. Initial advisory API and record model.
2. Manual JSON ingestion, validation, duplicate detection, and source tracking.
3. Guarded IMD connector configuration without live fetching by default.
4. Schema-driven normalization and dry-run previews.
5. Reviewed import with explicit commit and rejection reports.
6. Freshness/source-health checks and operations reporting.
7. React dashboard for advisories and source state.
8. Import audit metadata without bulletin text or credentials.
9. Shared bearer-token protection for admin routes.
10. Docker, CI, readiness endpoints, and database migrations.
11. Synthetic pilot workflow tests and pilot checklist.
12. Mobile layout, timeouts, offline handling, and manual UI checks.
13. Pilot-readiness diagnostic and supervised field-review guide.
14. Validity-window edge coverage and data-quality matrix.
15. Atomic batch commits and rollback on unexpected failures.

The provided cumulative archive is the source baseline for this bundle. Its tests and frontend were re-run during consolidation; migration and validation behavior were strengthened here. Individual Milestone 1–9 ZIPs were not present among the supplied files, so their separate historical artifacts could not be compared. This repository consolidates the cumulative implementation rather than claiming byte-for-byte preservation of each milestone archive.

## Safety and trust boundaries

- `source_verified` is always `false`; no software check proves official origin or reuse rights.
- Synthetic normalized imports are labeled demo by default. Do not change that label without a human review and documented source evidence.
- Missing validity, invalid or naive timestamps, expired/future windows, old retrievals, and unknown/stale/failed source health do not pass the current-display gate.
- A passing current check means only that the stored timestamps and local source-status metadata meet configured rules at request time.
- The app does not generate marine forecasts, interpret warning severity, or replace official information or fisher judgment.

## Data migrations

Run `alembic upgrade head` before starting the backend or importer. Revision `0001_initial` defines the consolidated schema explicitly. Revision `0002_legacy` detects the pre-consolidation schema (`source`, `source_id`, `sources`, and prior audit columns), copies existing rows into current tables, preserves record IDs and audit counts, then removes the renamed legacy tables. Back up any database before migration. The conversion downgrade is intentionally unsupported; restore a database backup for rollback.
