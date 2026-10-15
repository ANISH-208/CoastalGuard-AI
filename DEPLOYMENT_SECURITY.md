# Deployment security checklist

This project is a prototype security baseline, not a production identity or safety service.

## Required before deployment

- Use HTTPS and a managed secret store. Keep `.env`, database files, reports, and backups private.
- Replace the shared admin bearer token with individual operator accounts, roles, rotation, and revocation.
- Set exact trusted `CORS_ALLOWED_ORIGINS`; do not use `*` or frontend-embedded credentials.
- Add rate limits, request logging that excludes authorization headers and bulletin bodies, error monitoring, and alerting.
- Configure database backups and test restore. Back up before every schema migration; the legacy conversion has no downgrade.
- Review source access rights, schema, data reuse, and retention. The adapter's safe host check does not prove permission or authenticity.
- Set explicit advisory and source freshness thresholds with operational owners. They are display rules, not official bulletin validity or safety limits.
- Perform security and field usability reviews before any public pilot.

## Available protections

- Admin routes fail closed when `ADMIN_API_TOKEN` is absent or blank.
- Admin API and import-audit endpoints require bearer authentication.
- CORS uses an explicit origin allowlist and credentials are disabled.
- JSON file imports have configurable byte and record limits; IMD requests have a bounded timeout and response body cap.
- Import batches write advisories, source status, and commit audit metadata in one transaction.
- Docker runs the API as a non-root user and binds published API port to loopback by default.
- Liveness (`/health`) and database readiness (`/ready`) are separate.

These controls do not establish source verification, per-operator attribution, production authorization, or marine safety.
