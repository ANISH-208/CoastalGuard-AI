def test_pilot_readiness_is_blocked_without_verified_source_or_review(client):
    response = client.get('/api/v1/operations/pilot-readiness')
    assert response.status_code == 200
    body = response.json()
    assert body['readiness'] == 'blocked'
    assert body['checks']['official_source_access_and_schema_verified'] is False
    assert body['checks']['community_review_completed'] is False
    assert body['checks']['field_validation_completed'] is False
    assert 'official_source_access_and_schema_verified' in body['blockers']
    assert 'community_review_completed' in body['blockers']
    assert 'field_validation_completed' in body['blockers']


def test_pilot_readiness_reports_demo_data_and_empty_source_state(client):
    body = client.get('/api/v1/operations/pilot-readiness').json()
    assert body['counts']['sources'] == 0
    assert body['counts']['advisories'] == 0
    assert body['checks']['all_sources_healthy'] is False
    assert body['checks']['at_least_one_record_passes_current_checks'] is False


def test_pilot_readiness_never_claims_safety_certification(client):
    body = client.get('/api/v1/operations/pilot-readiness').json()
    assert 'not a safety certification' in body['safety_notice'].lower()
