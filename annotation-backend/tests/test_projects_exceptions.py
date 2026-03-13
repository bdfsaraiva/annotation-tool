import pytest
from fastapi import HTTPException

from app.api import projects as projects_api
from app.models import User


class FailingSession:
    def query(self, *args, **kwargs):
        raise Exception("boom")


@pytest.mark.anyio
async def test_list_user_projects_exception():
    user = User(id=1, username="x", hashed_password="x", is_admin=True)
    with pytest.raises(HTTPException):
        await projects_api.list_user_projects(db=FailingSession(), current_user=user)


@pytest.mark.anyio
async def test_get_project_exception():
    user = User(id=1, username="x", hashed_password="x", is_admin=True)
    with pytest.raises(HTTPException):
        await projects_api.get_project(project_id=1, db=FailingSession(), current_user=user)
