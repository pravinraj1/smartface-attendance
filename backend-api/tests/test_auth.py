"""Authentication and token-handling tests."""
import uuid

from conftest import ADMIN_EMAIL, ADMIN_PASSWORD, VIEWER_ROLE, HR_ROLE, _suffix


def test_login_success(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("access_token")
    assert body.get("refresh_token")


def test_login_wrong_password(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": "WrongPass999"},
    )
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 403  # no bearer -> 403


def test_me_with_token(client, admin_headers):
    r = client.get("/api/v1/auth/me", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["email"] == ADMIN_EMAIL


def test_weak_password_rejected(client, admin_headers):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"weak_{_suffix()}@t.com",
            "full_name": "Weak",
            "password": "abcdefgh",  # letters only -> must be rejected
            "role_id": HR_ROLE,
        },
        headers=admin_headers,
    )
    assert r.status_code == 422


def test_strong_password_ok_and_cleanup(client, admin_headers, db_call):
    email = f"str_{_suffix()}@t.com"
    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Strong",
            "password": "StrongPass1",
            "role_id": VIEWER_ROLE,
        },
        headers=admin_headers,
    )
    assert r.status_code == 200
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongPass1"})
    assert login.status_code == 200
    # refresh token revocation: works before logout, fails after
    refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    assert refresh.status_code == 200
    # logout revokes
    assert client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {login.json()['access_token']}"}).status_code == 200
    revoked = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login.json()["refresh_token"]},
    )
    assert revoked.status_code == 401
    # cleanup user on a dedicated engine/session (same loop)
    from sqlalchemy import select
    from app.models.user import User

    async def _del(db):
        u = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if u:
            await db.delete(u)
            await db.commit()
    db_call(_del)
