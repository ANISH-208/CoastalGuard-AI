def test_demo_fixtures_are_opt_in(client):
    response = client.get("/api/v1/advisories?include_expired=true")
    assert response.status_code == 200
    assert response.json() == []
