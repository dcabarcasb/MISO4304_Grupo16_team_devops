def test_health_without_token(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "host" in data


def test_health_reports_configured_version(app, client):
    response = client.get("/health")
    assert response.get_json()["version"] == app.config["APP_VERSION"]


def test_health_ignores_authorization_header(client, bad_token_headers):
    response = client.get("/health", headers=bad_token_headers)
    assert response.status_code == 200
