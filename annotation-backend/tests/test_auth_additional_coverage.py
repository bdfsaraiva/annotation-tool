import pytest
from fastapi import HTTPException
from jose import jwt
from sqlalchemy.orm import Session

from app import auth
from app.config import get_settings
from conftest import create_user


def test_register_duplicate_and_commit_error(client, db_session, monkeypatch):
    create_user(db_session, "dup_register", "pass", is_admin=False)

    response = client.post(
        "/auth/register",
        json={"username": "dup_register", "password": "pass", "is_admin": False}
    )
    assert response.status_code == 400

    def boom(self):
        raise RuntimeError("boom")

    monkeypatch.setattr(Session, "commit", boom, raising=True)

    response = client.post(
        "/auth/register",
        json={"username": "new_register", "password": "pass", "is_admin": False}
    )
    assert response.status_code == 500


@pytest.mark.anyio
async def test_get_current_user_missing_user(db_session):
    token = auth.create_access_token({"sub": "ghost_user"})
    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(token=token, db=db_session)
    assert exc.value.status_code == 401


@pytest.mark.anyio
async def test_refresh_access_token_invalid_cases(db_session):
    settings = get_settings()

    bad_type = jwt.encode(
        {"sub": "ghost_user", "type": "access"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    with pytest.raises(HTTPException):
        await auth.refresh_access_token(refresh_token=bad_type, db=db_session)

    missing_sub = jwt.encode(
        {"type": "refresh"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    with pytest.raises(HTTPException):
        await auth.refresh_access_token(refresh_token=missing_sub, db=db_session)

    with pytest.raises(HTTPException):
        await auth.refresh_access_token(refresh_token="not-a-token", db=db_session)
