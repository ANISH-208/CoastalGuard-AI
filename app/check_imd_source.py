import json
import os
import sys

from app.sources.imd import IMDSourceConfig, SourceConfigurationError, SourceFetchError, fetch_imd_payload, summarize_payload


def main() -> int:
    config = IMDSourceConfig(
        enabled=os.getenv("IMD_MARINE_ENABLED", "false").lower() == "true",
        endpoint_url=os.getenv("IMD_MARINE_ENDPOINT") or None,
        auth_header_name=os.getenv("IMD_AUTH_HEADER_NAME") or None,
        auth_header_value=os.getenv("IMD_AUTH_HEADER_VALUE") or None,
        timeout_seconds=float(os.getenv("IMD_TIMEOUT_SECONDS", "10")),
    )
    try:
        payload = fetch_imd_payload(config)
    except (SourceConfigurationError, SourceFetchError) as exc:
        print(f"IMD source check failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(summarize_payload(payload), indent=2))
    print(
        "No records were saved or published. Review the official schema and access terms "
        "before implementing normalization or importing data."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
