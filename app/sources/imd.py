from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse
import re

import httpx


class SourceConfigurationError(RuntimeError):
    pass


class SourceFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class IMDSourceConfig:
    enabled: bool
    endpoint_url: str | None
    auth_header_name: str | None = None
    auth_header_value: str | None = None
    timeout_seconds: float = 10.0
    max_response_bytes: int = 5_000_000


def validate_config(config: IMDSourceConfig) -> None:
    if not config.enabled:
        raise SourceConfigurationError(
            "IMD connector is disabled. Confirm access and set IMD_MARINE_ENABLED=true only after approval."
        )
    if not config.endpoint_url:
        raise SourceConfigurationError("Set IMD_MARINE_ENDPOINT to an endpoint documented for your approved access.")
    parsed = urlparse(config.endpoint_url)
    if parsed.scheme != "https" or parsed.hostname != "api.imd.gov.in":
        raise SourceConfigurationError(
            "For safety, the IMD connector only accepts HTTPS endpoints on api.imd.gov.in."
        )
    if (config.auth_header_name is None) != (config.auth_header_value is None):
        raise SourceConfigurationError(
            "Configure both IMD_AUTH_HEADER_NAME and IMD_AUTH_HEADER_VALUE, or neither."
        )
    if not 1 <= config.timeout_seconds <= 60:
        raise SourceConfigurationError("IMD timeout must be between 1 and 60 seconds.")
    if not 1 <= config.max_response_bytes <= 50_000_000:
        raise SourceConfigurationError("IMD response size limit must be between 1 and 50,000,000 bytes.")
    if config.auth_header_name and not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", config.auth_header_name):
        raise SourceConfigurationError("Authentication header name is invalid.")


def fetch_imd_payload(config: IMDSourceConfig) -> Any:
    """Fetch raw JSON from an explicitly configured IMD endpoint.

    This function deliberately does not guess an authentication scheme, infer validity
    fields, translate warning text, or import records into the public API database.
    Only use it after confirming account access and data-use permissions.
    """
    validate_config(config)
    headers = {"Accept": "application/json", "User-Agent": "CoastGuardAI/0.1 (prototype)"}
    if config.auth_header_name and config.auth_header_value:
        headers[config.auth_header_name] = config.auth_header_value

    try:
        with httpx.stream(
            "GET", config.endpoint_url,
            headers=headers,
            timeout=config.timeout_seconds,
            follow_redirects=False,
        ) as response:
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "json" not in content_type:
                raise SourceFetchError("IMD endpoint did not return a JSON content type.")
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > config.max_response_bytes:
                raise SourceFetchError("IMD response exceeds the configured size limit.")
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > config.max_response_bytes:
                    raise SourceFetchError("IMD response exceeds the configured size limit.")
    except httpx.HTTPError as exc:
        raise SourceFetchError(f"IMD request failed: {type(exc).__name__}") from exc

    try:
        import json
        payload = json.loads(body)
    except ValueError as exc:
        raise SourceFetchError("IMD endpoint returned invalid JSON.") from exc

    if not isinstance(payload, (dict, list)):
        raise SourceFetchError("Unexpected JSON shape: expected an object or array.")
    return payload


def summarize_payload(payload: Any) -> dict[str, Any]:
    """Return safe structural metadata only; do not treat it as a safety interpretation."""
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
        records = payload["data"]
    else:
        records = [payload]
    return {
        "json_root_type": "array" if isinstance(payload, list) else "object",
        "record_count": len(records),
        "record_object_count": sum(isinstance(record, dict) for record in records),
        "note": "Structure check only; records have not been normalized or validated as current advisories.",
    }
