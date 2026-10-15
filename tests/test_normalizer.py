from app.sources.normalizer import FieldMapping, normalize_payload


def mapping():
    return FieldMapping(
        source_name="SYNTHETIC_TEST",
        record_id="id",
        title="headline",
        original_text="message",
        region="area.name",
        issued_at="issued",
        valid_from="valid.start",
        valid_until="valid.end",
    )


def test_normalizer_maps_only_explicit_fields():
    payload = [{
        "id": "synthetic-1",
        "headline": "DEMO ONLY — NOT A REAL WARNING",
        "message": "Synthetic fixture only.",
        "area": {"name": "DEMO_REGION"},
        "issued": "2030-01-01T00:00:00Z",
        "valid": {"start": "2030-01-01T00:00:00Z", "end": "2030-01-01T01:00:00Z"},
        "unmapped_secret_or_field": "must be ignored",
    }]
    result = normalize_payload(payload, mapping(), is_demo=True)
    assert len(result.records) == 1
    assert result.records[0].source_record_id == "synthetic-1"
    assert result.records[0].region == "DEMO_REGION"
    assert result.records[0].is_demo is True
    assert result.rejected == []


def test_normalizer_rejects_missing_required_source_fields():
    result = normalize_payload([{"id": "missing-other-fields"}], mapping())
    assert result.records == []
    assert len(result.rejected) == 1
    assert result.rejected[0]["index"] == 0


def test_normalizer_rejects_unknown_timestamp_format():
    payload = [{
        "id": "synthetic-2",
        "headline": "DEMO ONLY — NOT A REAL WARNING",
        "message": "Synthetic fixture only.",
        "area": {"name": "DEMO_REGION"},
        "issued": 1700000000,
        "valid": {"start": "2030-01-01T00:00:00Z", "end": "2030-01-01T01:00:00Z"},
    }]
    result = normalize_payload(payload, mapping())
    assert result.records == []
    assert "Timestamp must be an ISO-8601" in result.rejected[0]["reason"]


def test_normalizer_supports_wrapped_data_array():
    result = normalize_payload({"data": [{
        "id": "synthetic-3",
        "headline": "DEMO ONLY — NOT A REAL WARNING",
        "message": "Synthetic fixture only.",
        "area": {"name": "DEMO_REGION"},
        "issued": "2030-01-01T00:00:00Z",
        "valid": {"start": "2030-01-01T00:00:00Z", "end": "2030-01-01T01:00:00Z"},
    }]}, mapping())
    assert len(result.records) == 1
