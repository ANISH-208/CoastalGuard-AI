# CoastGuard AI

CoastGuard AI is a Coastal Karnataka prototype for reviewing marine bulletin records, their validity windows, and source health. It supports locally supplied JSON and has a guarded IMD connector shell. **It currently has no verified live IMD or INCOIS feed and must not be used alone to decide whether to go to sea.** A record passing the app's current checks is not proof that its source is authentic, its content is accurate, or its reuse is permitted.

## Capabilities

- FastAPI backend with explicit validation, duplicate detection, source status, import audit history, readiness checks, and token-protected admin routes.
- Local JSON normalization with explicit field mappings, dry-run by default, review reports, bounded input size, and opt-in database commit.
- Advisory visibility gates for time zone, validity window, retrieval age, and source freshness. Responses state why a record is not current and always mark source verification as unconfirmed.
- React dashboard with source/validity metadata, stale reasons, offline/error states, and links to official information.
- Alembic migrations, Docker Compose, CI, and synthetic regression fixtures.

See [Architecture and feature inventory](docs/ARCHITECTURE.md), [pilot checklist](docs/PILOT_VALIDATION_CHECKLIST.md), [data quality matrix](docs/DATA_QUALITY_TEST_MATRIX.md), and [deployment security notes](DEPLOYMENT_SECURITY.md).

## Run locally

Python 3.12+ and Node.js 22+ are recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m pytest -q
uvicorn app.main:app --reload
```

For the dashboard, in another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open the Vite URL (normally `http://127.0.0.1:5173`). `GET /health` checks app liveness; `GET /ready` checks database connectivity; `/docs` shows API documentation. Operations health and source status are at `/api/v1/operations/health` and `/api/v1/sources/status`. Admin routes stay disabled until `ADMIN_API_TOKEN` is configured. Never place that token in the frontend.

## Local JSON review

The sample in `examples/bulletin_template.json` is synthetic. Run a dry-run with explicit source-to-app mappings:

```bash
python -m app.import_normalized examples/bulletin_template.json \
  --source-name SYNTHETIC_TEST \
  --id-field id --title-field title --text-field message \
  --region-field area.name --issued-field issued_at \
  --valid-from-field validity.start --valid-until-field validity.end \
  --report review-report.json
```

Review the report before writing. Add `--commit` only after reviewing both content and reuse permission. Imports with rejected rows are blocked unless `--allow-partial` is explicitly supplied. The CLI stores only counts and import metadata in its audit row; the local review report contains record content, so keep it private. Local imports do not establish authenticity or official status. Do not label records verified based only on a source name.

## Docker

Copy `.env.example` to `.env`, set separate random values for `POSTGRES_PASSWORD` and `ADMIN_API_TOKEN`, and set `CORS_ALLOWED_ORIGINS` to the exact frontend origin before starting:

```bash
docker compose up --build -d
docker compose ps
curl http://127.0.0.1:8000/ready
```

The API binds to loopback by default. HTTPS, operator identity and authorization, secret rotation, rate limits, backups, and production monitoring still need deployment-specific setup. See [DEPLOYMENT_SECURITY.md](DEPLOYMENT_SECURITY.md).

## Data sources and safety limits

The IMD adapter is disabled by default. It restricts requests to the official API host and does not normalize, save, or publish fetched content. Configure it only after confirming access method, credentials, schema, and reuse terms with the source. INCOIS official forecast information is linked in the dashboard; no INCOIS API client is present. Official source pages: [IMD API reference](https://api.imd.gov.in/public/api_reference.html) and [INCOIS Ocean State Forecast](https://incois.gov.in/oceanservices/osfforecast.jsp).

All tests use synthetic content. They verify prototype behavior only; they do not validate live feeds, forecast accuracy, warning authenticity, local community needs, or operational safety. Field validation requires consent and supervised review.

## Environment settings

The complete list is in [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md). The 24-hour freshness defaults are configurable prototype display thresholds, not official validity rules or validated safety thresholds. The IMD request adapter stays disabled unless explicitly enabled and configured after access approval.

## Windows setup

In PowerShell, create and activate the virtual environment, then run the same install/migration/test commands:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python -m pytest -q
uvicorn app.main:app --reload
```

In a second PowerShell window run `cd frontend`, `npm ci`, and `npm run dev`.

## Troubleshooting

- **Admin route returns 503:** configure `ADMIN_API_TOKEN` in the backend environment and restart it. Keep the secret out of frontend configuration.
- **Dashboard says API unavailable:** start the backend and check `http://127.0.0.1:8000/ready`; set `VITE_API_BASE_URL` in `frontend/.env` only if the API uses another origin.
- **Database readiness fails:** verify `DATABASE_URL`, database reachability, then run `alembic upgrade head`.
- **Importer cannot find tables:** run the migration before invoking the importer.
- **IMD source check stops safely:** expected with the default disabled configuration. Confirm documented access and permissions before setting `IMD_MARINE_ENABLED=true`.
- **Vite dependency install fails:** use Node.js 22 and run `npm ci` in `frontend`.
