import pytest

from app.dependencies import get_current_user, verify_project_access
from app.auth import create_access_token
from conftest import create_user, create_project, create_chat_room, assign_user


@pytest.mark.anyio
async def test_get_current_user_success(db_session):
    user = create_user(db_session, "dep_user", "pass", is_admin=False)
    token = create_access_token({"sub": user.username})
    current = await get_current_user(token=token, db=db_session)
    assert current.username == user.username


@pytest.mark.anyio
async def test_verify_project_access_admin(db_session):
    admin = create_user(db_session, "dep_admin", "pass", is_admin=True)
    project = create_project(db_session, name="dep_proj")
    # Should not raise for admin
    await verify_project_access(project_id=project.id, db=db_session, current_user=admin)


@pytest.mark.anyio
async def test_verify_project_access_forbidden(db_session):
    user = create_user(db_session, "dep_user2", "pass", is_admin=False)
    project = create_project(db_session, name="dep_proj2")
    with pytest.raises(Exception):
        await verify_project_access(project_id=project.id, db=db_session, current_user=user)
