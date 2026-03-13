import pytest

from app.auth import get_current_user, get_current_admin_user, refresh_access_token, create_refresh_token
from conftest import create_user


@pytest.mark.anyio
async def test_auth_get_current_user_and_admin_errors(db_session):
    user = create_user(db_session, "auth_user", "pass", is_admin=False)
    admin = create_user(db_session, "auth_admin", "pass", is_admin=True)

    # Non-admin should fail admin check
    with pytest.raises(Exception):
        await get_current_admin_user(current_user=user)

    # Admin should pass
    result = await get_current_admin_user(current_user=admin)
    assert result.username == admin.username


@pytest.mark.anyio
async def test_refresh_access_token_user_missing(db_session):
    token = create_refresh_token({"sub": "ghost"})
    with pytest.raises(Exception):
        await refresh_access_token(refresh_token=token, db=db_session)
