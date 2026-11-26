"""Authentication API integration tests."""

from uuid import UUID

from service_desk_api.models.auth_session import AuthSession
from service_desk_api.models.user import User


def _register_and_login(client, email="session@example.com"):
    payload = {
        "email": email,
        "full_name": "Session User",
        "password": "a-very-long-test-password",
    }
    registration = client.post("/api/v1/auth/register", json=payload)
    assert registration.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": payload["password"]},
    )
    assert login.status_code == 200
    return registration.json(), login.json()


def test_register_login_and_get_current_user(client):
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": "VITOR@example.com", "full_name": "Vitor Silveira",
              "password": "a-very-long-test-password"},
    )
    assert registration.status_code == 201
    user = registration.json()
    assert user["email"] == "vitor@example.com"
    assert user["role"] == "requester"
    assert "password_hash" not in user

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "vitor@example.com", "password": "a-very-long-test-password"},
    )
    assert login.status_code == 200
    token_data = login.json()
    assert token_data["token_type"] == "bearer"
    assert token_data["expires_in"] > 0
    assert token_data["refresh_token"]

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer " + token_data["access_token"]},
    )
    assert profile.status_code == 200
    assert profile.json()["id"] == user["id"]


def test_registration_rejects_duplicate_email(client):
    payload = {"email": "duplicate@example.com", "full_name": "Duplicate User",
               "password": "a-very-long-test-password"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


def test_login_rejects_invalid_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "person@example.com", "full_name": "Example Person",
              "password": "a-very-long-test-password"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_profile_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_invalid_token_is_rejected(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer definitely-not-a-valid-token"},
    )
    assert response.status_code == 401


def test_login_uses_same_generic_error_for_unknown_email(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "a-very-long-test-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_inactive_user_cannot_login_or_keep_using_existing_token(client):
    registration, login = _register_and_login(client, "inactive@example.com")
    with client.app.state.testing_session_factory() as session:
        user = session.get(User, UUID(registration["id"]))
        user.is_active = False
        session.commit()

    rejected_login = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "a-very-long-test-password"},
    )
    assert rejected_login.status_code == 401
    rejected_profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert rejected_profile.status_code == 401


def test_production_rejects_default_or_short_jwt_secret():
    import pytest
    from pydantic import SecretStr

    from service_desk_api.config import Settings

    insecure_settings = Settings(
        environment="production",
        jwt_secret_key=SecretStr("short-secret"),
    )
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        insecure_settings.validate_security_settings()


def test_production_accepts_long_unique_jwt_secret():
    from pydantic import SecretStr

    from service_desk_api.config import Settings

    settings = Settings(
        environment="production",
        jwt_secret_key=SecretStr("a-unique-production-secret-with-more-than-32-characters"),
    )
    settings.validate_security_settings()


def test_login_is_rate_limited_after_five_failed_passwords(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "limited@example.com", "full_name": "Limited User",
              "password": "a-very-long-test-password"},
    )
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "limited@example.com", "password": "wrong-password"},
        )
        assert response.status_code == 401
    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "limited@example.com", "password": "a-very-long-test-password"},
    )
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


def test_successful_login_clears_email_failure_counter(client):
    payload = {
        "email": "reset-limit@example.com",
        "full_name": "Reset Limit",
        "password": "a-very-long-test-password",
    }
    client.post("/api/v1/auth/register", json=payload)
    for _ in range(4):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": payload["email"], "password": "wrong-password"},
        )
        assert response.status_code == 401
    successful = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert successful.status_code == 200
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": payload["email"], "password": "wrong-password"},
        )
        assert response.status_code == 401


def test_refresh_rotates_token_and_rejects_reuse(client):
    _, login = _register_and_login(client, "rotation@example.com")
    old_refresh = login["refresh_token"]
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert rotated.status_code == 200
    new_refresh = rotated.json()["refresh_token"]
    assert new_refresh != old_refresh

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401
    revoked = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert revoked.status_code == 401


def test_logout_revokes_refresh_token(client):
    _, login = _register_and_login(client, "logout@example.com")
    refresh_token = login["refresh_token"]
    logout = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 204
    rejected = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert rejected.status_code == 401


def test_inactive_user_cannot_refresh_session(client):
    registration, login = _register_and_login(client, "inactive-refresh@example.com")
    refresh_token = login["refresh_token"]
    with client.app.state.testing_session_factory() as session:
        user = session.get(User, UUID(registration["id"]))
        user.is_active = False
        session.commit()
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401


def test_refresh_tokens_are_stored_only_as_hashes(client):
    _, login = _register_and_login(client, "hash@example.com")
    token = login["refresh_token"]
    with client.app.state.testing_session_factory() as session:
        stored = session.query(AuthSession).one()
        assert stored.token_hash != token
        assert len(stored.token_hash) == 64
