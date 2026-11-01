import uuid

from app.models import BlacklistEmail

VALID_EMAIL = "blocked@example.com"
VALID_UUID = str(uuid.uuid4())


def _payload(**overrides):
    body = {
        "email": VALID_EMAIL,
        "app_uuid": VALID_UUID,
        "blocked_reason": "spam",
    }
    body.update(overrides)
    return body


def test_post_requires_token(client):
    response = client.post("/blacklists", json=_payload())
    assert response.status_code == 401


def test_post_rejects_wrong_token(client, bad_token_headers):
    response = client.post(
        "/blacklists", json=_payload(), headers=bad_token_headers
    )
    assert response.status_code == 403


def test_post_creates_entry(client, auth_headers):
    response = client.post("/blacklists", json=_payload(), headers=auth_headers)
    assert response.status_code == 201
    assert response.get_json()["created"] is True


def test_post_duplicate_returns_conflict(client, auth_headers):
    client.post("/blacklists", json=_payload(), headers=auth_headers)
    response = client.post("/blacklists", json=_payload(), headers=auth_headers)
    assert response.status_code == 409
    assert response.get_json()["created"] is False


def test_post_persists_entry(app, client, auth_headers):
    client.post(
        "/blacklists",
        json=_payload(),
        headers={**auth_headers, "X-Forwarded-For": "203.0.113.7, 10.0.0.1"},
    )
    entry = BlacklistEmail.query.filter_by(email=VALID_EMAIL).one()
    assert entry.app_uuid == VALID_UUID
    assert entry.blocked_reason == "spam"
    assert entry.request_ip == "203.0.113.7"
    assert entry.created_at is not None


def test_post_normalizes_email(client, auth_headers):
    client.post(
        "/blacklists", json=_payload(email="Blocked@Example.COM"), headers=auth_headers
    )
    response = client.post("/blacklists", json=_payload(), headers=auth_headers)
    assert response.status_code == 409


def test_post_missing_body(client, auth_headers):
    response = client.post("/blacklists", headers=auth_headers)
    assert response.status_code == 400
    errors = response.get_json()["errors"]
    assert "email" in errors
    assert "app_uuid" in errors


def test_post_invalid_uuid(client, auth_headers):
    response = client.post(
        "/blacklists", json=_payload(app_uuid="not-a-uuid"), headers=auth_headers
    )
    assert response.status_code == 400


def test_post_invalid_email(client, auth_headers):
    response = client.post(
        "/blacklists", json=_payload(email="not-an-email"), headers=auth_headers
    )
    assert response.status_code == 400


def test_post_reason_too_long(client, auth_headers):
    response = client.post(
        "/blacklists", json=_payload(blocked_reason="x" * 256), headers=auth_headers
    )
    assert response.status_code == 400


def test_post_optional_reason(client, auth_headers):
    body = _payload()
    body.pop("blocked_reason")
    response = client.post("/blacklists", json=body, headers=auth_headers)
    assert response.status_code == 201


def test_get_requires_token(client):
    response = client.get(f"/blacklists/{VALID_EMAIL}")
    assert response.status_code == 401


def test_get_rejects_wrong_token(client, bad_token_headers):
    response = client.get(f"/blacklists/{VALID_EMAIL}", headers=bad_token_headers)
    assert response.status_code == 403


def test_get_is_case_insensitive(client, auth_headers):
    client.post("/blacklists", json=_payload(), headers=auth_headers)
    response = client.get("/blacklists/BLOCKED@example.com", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json()["is_blacklisted"] is True


def test_get_blacklisted(client, auth_headers):
    client.post("/blacklists", json=_payload(), headers=auth_headers)
    response = client.get(f"/blacklists/{VALID_EMAIL}", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["is_blacklisted"] is True
    assert data["blocked_reason"] == "spam"


def test_get_not_blacklisted(client, auth_headers):
    response = client.get("/blacklists/unknown@example.com", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["is_blacklisted"] is False
    assert data["blocked_reason"] is None
