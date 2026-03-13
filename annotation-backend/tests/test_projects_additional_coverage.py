import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import crud, models
from app.api import projects as projects_api
from conftest import (
    create_user,
    create_project,
    create_chat_room,
    create_message,
    assign_user,
    auth_headers
)


def test_project_assign_remove_exception_branches(client, db_session, monkeypatch):
    admin = create_user(db_session, "admin_proj_exc", "pass", is_admin=True)
    user = create_user(db_session, "user_proj_exc", "pass", is_admin=False)
    project = create_project(db_session, name="proj_exc")
    headers = auth_headers(client, "admin_proj_exc", "pass")

    def boom(self):
        raise RuntimeError("boom")

    original_commit = Session.commit
    monkeypatch.setattr(Session, "commit", boom, raising=True)

    response = client.post(f"/projects/{project.id}/assign/{user.id}", headers=headers)
    assert response.status_code == 500

    monkeypatch.setattr(Session, "commit", original_commit, raising=True)
    assign_user(db_session, user.id, project.id)
    monkeypatch.setattr(Session, "commit", boom, raising=True)

    response = client.delete(f"/projects/{project.id}/assign/{user.id}", headers=headers)
    assert response.status_code == 500

    response = client.delete(
        f"/projects/{project.id}/assign/{user.id}",
        headers=auth_headers(client, "user_proj_exc", "pass")
    )
    assert response.status_code == 403


def test_chat_room_access_branches(client, db_session):
    user = create_user(db_session, "user_chat_access", "pass", is_admin=False)
    project = create_project(db_session, name="proj_chat_access")
    room = create_chat_room(db_session, project.id, name="room_chat_access")
    create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hi")
    headers = auth_headers(client, "user_chat_access", "pass")

    response = client.get(f"/projects/{project.id}/chat-rooms", headers=headers)
    assert response.status_code == 403

    response = client.get(f"/projects/{project.id}/chat-rooms/{room.id}", headers=headers)
    assert response.status_code == 403

    response = client.get(f"/projects/{project.id}/chat-rooms/{room.id}/messages", headers=headers)
    assert response.status_code == 403

    response = client.get("/projects/999/chat-rooms", headers=headers)
    assert response.status_code == 404

    response = client.get("/projects/999/chat-rooms/1", headers=headers)
    assert response.status_code == 404

    response = client.get("/projects/999/chat-rooms/1/messages", headers=headers)
    assert response.status_code == 404


def test_chat_room_completion_existing_and_missing(client, db_session):
    user = create_user(db_session, "user_completion", "pass", is_admin=False)
    project = create_project(db_session, name="proj_completion")
    room = create_chat_room(db_session, project.id, name="room_completion")
    assign_user(db_session, user.id, project.id)
    headers = auth_headers(client, "user_completion", "pass")

    crud.upsert_chat_room_completion(db_session, room.id, project.id, user.id, True)
    response = client.get(
        f"/projects/{project.id}/chat-rooms/{room.id}/completion",
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["is_completed"] is True

    response = client.get(
        f"/projects/{project.id}/chat-rooms/999/completion",
        headers=headers
    )
    assert response.status_code == 404

    response = client.put(
        f"/projects/{project.id}/chat-rooms/999/completion",
        json={"is_completed": True},
        headers=headers
    )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_project_users_exception():
    class FailingSession:
        def query(self, *args, **kwargs):
            raise RuntimeError("boom")

    current_user = models.User(
        id=1,
        username="admin_fail",
        hashed_password="x",
        is_admin=True
    )
    with pytest.raises(HTTPException) as exc:
        await projects_api.get_project_users(1, db=FailingSession(), current_user=current_user)
    assert exc.value.status_code == 500
