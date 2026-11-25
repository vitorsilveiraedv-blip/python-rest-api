"""Authentication API integration tests."""

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
