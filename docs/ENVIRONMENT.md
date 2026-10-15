# Environment variables

Values in `.env.example` are placeholders/defaults. Never commit a populated `.env`.

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy database connection | `sqlite:///./coastguard.db` |
| `APP_ENV` | Runtime mode; production disables development table creation | `development` |
| `LOAD_DEMO_FIXTURES` | Load explicitly synthetic fixtures outside production | `false` |
| `ADVISORY_MAX_AGE_HOURS` | Maximum local retrieval age for current-display checks | `24` |
| `SOURCE_STALE_AFTER_HOURS` | Maximum age of recorded source success | `24` |
| `ADMIN_API_TOKEN` | Shared prototype bearer secret; blank disables admin routes | unset |
| `CORS_ALLOWED_ORIGINS` | Comma-separated trusted browser origins | localhost Vite origins |
| `MAX_IMPORT_FILE_BYTES` | Maximum local JSON file size | `5000000` |
| `MAX_IMPORT_RECORDS` | Maximum number of input records per JSON import | `5000` |
| `IMD_MARINE_ENABLED` | Whether the manual source-check command may request IMD | `false` |
| `IMD_MARINE_ENDPOINT` | Explicit endpoint after authorized access is confirmed | unset |
| `IMD_AUTH_HEADER_NAME`, `IMD_AUTH_HEADER_VALUE` | Optional source-prescribed auth header, only if documented | unset |
| `IMD_TIMEOUT_SECONDS` | IMD request timeout, constrained to 1–60 seconds | `10` |
| `POSTGRES_PASSWORD` | Docker Compose database password | unset; required for Compose |

The initial freshness values are configurable prototype defaults, not validated operational thresholds. Choose them with source operators after examining publication and update cadence. The IMD adapter is disabled by default and does not write or publish fetched data. The IMD API reference lists the sea-area bulletin endpoint at `/api/v1/seabulletin`; access method, credentials, data-use terms, and actual response behavior still require confirmation through an authorized account.

Local shell:

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Set secrets in the environment or a private secret manager. Do not paste secrets into README, frontend variables, issue reports, or import reports.
