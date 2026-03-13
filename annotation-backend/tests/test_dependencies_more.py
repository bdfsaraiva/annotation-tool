import pytest
from jose import jwt

from app.dependencies import get_db, get_current_user, get_current_admin_user, verify_project_access
from app.config import get_settings
from app.auth import create_access_token, create_refresh_token
from conftest import create_user, create_project, assign_user


def test_get_db_generator():
    gen = get_db()
    db = next(gen)
    assert db is not None
    try:
        gen.close()
    except Exception:
        pass


@pytest.mark.anyio
async def test_get_current_user_missing_sub(db_session):
    token = create_access_token({"foo": "bar"})
    with pytest.raises(Exception):
        await get_current_user(token=token, db=db_session)


@pytest.mark.anyio
async def test_get_current_user_invalid_token(db_session):
    with pytest.raises(Exception):
        await get_current_user(token="invalid.token.value", db=db_session)


@pytest.mark.anyio
async def test_get_current_user_user_not_found(db_session):
    token = create_access_token({"sub": "ghost"})
    with pytest.raises(Exception):
        await get_current_user(token=token, db=db_session)


@pytest.mark.anyio
async def test_get_current_admin_user_forbidden(db_session):
    user = create_user(db_session, "dep_non_admin", "pass", is_admin=False)
    with pytest.raises(Exception):
        await get_current_admin_user(current_user=user)


@pytest.mark.anyio
async def test_verify_project_access_assigned(db_session):
    user = create_user(db_session, "dep_assigned", "pass", is_admin=False)
    project = create_project(db_session, name="dep_proj_assigned")
    assign_user(db_session, user.id, project.id)
    await verify_project_access(project_id=project.id, db=db_session, current_user=user)
