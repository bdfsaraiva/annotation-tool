from app.auth import create_access_token, create_refresh_token, verify_password, get_password_hash


def test_password_hashing_roundtrip():
    hashed = get_password_hash("secret")
    assert verify_password("secret", hashed)
    assert not verify_password("wrong", hashed)


def test_token_creation():
    access = create_access_token({"sub": "user1"})
    refresh = create_refresh_token({"sub": "user1"})
    assert isinstance(access, str) and isinstance(refresh, str)
    assert access != refresh


def test_register_login_refresh_me(client):
    # Register
    response = client.post("/auth/register", json={"username": "user1", "password": "pass", "is_admin": False})
    assert response.status_code == 200

    # Login
    response = client.post(
        "/auth/token",
        data={"username": "user1", "password": "pass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens and "refresh_token" in tokens

    # Me
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert response.status_code == 200
    assert response.json()["username"] == "user1"

    # Refresh
    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    refreshed = response.json()
    assert "access_token" in refreshed and "refresh_token" in refreshed


def test_login_invalid_password(client):
    client.post("/auth/register", json={"username": "user2", "password": "pass", "is_admin": False})
    response = client.post(
        "/auth/token",
        data={"username": "user2", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 401
