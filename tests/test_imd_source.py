import httpx
from contextlib import nullcontext
import pytest

from app.sources.imd import (
    IMDSourceConfig,
    SourceConfigurationError,
    SourceFetchError,
    fetch_imd_payload,
    summarize_payload,
)


def test_connector_disabled_by_default():
    config = IMDSourceConfig(enabled=False, endpoint_url=None)
    with pytest.raises(SourceConfigurationError):
        fetch_imd_payload(config)


def test_connector_rejects_non_imd_host():
    config = IMDSourceConfig(enabled=True, endpoint_url="https://example.com/api")
    with pytest.raises(SourceConfigurationError):
        fetch_imd_payload(config)


def test_connector_rejects_http_not_https():
    config = IMDSourceConfig(enabled=True, endpoint_url="http://api.imd.gov.in/api/v1/seabulletin")
    with pytest.raises(SourceConfigurationError):
        fetch_imd_payload(config)


def test_connector_rejects_incomplete_auth_header():
    config = IMDSourceConfig(
        enabled=True,
        endpoint_url="https://api.imd.gov.in/api/v1/seabulletin",
        auth_header_name="Authorization",
        auth_header_value=None,
    )
    with pytest.raises(SourceConfigurationError):
        fetch_imd_payload(config)


def test_fetch_json_with_mocked_response(monkeypatch):
    def fake_stream(*args, **kwargs):
        return nullcontext(httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json=[{"Id": "synthetic-1"}, {"Id": "synthetic-2"}],
            request=httpx.Request("GET", args[1]),
        ))

    monkeypatch.setattr(httpx, "stream", fake_stream)
    config = IMDSourceConfig(
        enabled=True,
        endpoint_url="https://api.imd.gov.in/api/v1/seabulletin",
    )
    payload = fetch_imd_payload(config)
    assert summarize_payload(payload)["record_count"] == 2


def test_non_json_response_is_rejected(monkeypatch):
    def fake_stream(*args, **kwargs):
        return nullcontext(httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="not json",
            request=httpx.Request("GET", args[1]),
        ))

    monkeypatch.setattr(httpx, "stream", fake_stream)
    config = IMDSourceConfig(
        enabled=True,
        endpoint_url="https://api.imd.gov.in/api/v1/seabulletin",
    )
    with pytest.raises(SourceFetchError):
        fetch_imd_payload(config)


def test_connector_rejects_unbounded_timeout():
    config = IMDSourceConfig(
        enabled=True,
        endpoint_url="https://api.imd.gov.in/api/v1/seabulletin",
        timeout_seconds=120,
    )
    with pytest.raises(SourceConfigurationError):
        fetch_imd_payload(config)


def test_fetch_rejects_response_over_size_limit(monkeypatch):
    def fake_stream(*args, **kwargs):
        return nullcontext(httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"{}",
            request=httpx.Request("GET", args[1]),
        ))

    monkeypatch.setattr(httpx, "stream", fake_stream)
    config = IMDSourceConfig(
        enabled=True,
        endpoint_url="https://api.imd.gov.in/api/v1/seabulletin",
        max_response_bytes=1,
    )
    with pytest.raises(SourceFetchError, match="size limit"):
        fetch_imd_payload(config)
