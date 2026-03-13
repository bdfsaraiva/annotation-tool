import json
import pytest

from app import crud, database
from conftest import (
    create_user,
    create_project,
    create_chat_room,
    create_message,
    assign_user,
    create_annotation,
    auth_headers
)


def test_projects_access_errors(client, db_session):
    admin = create_user(db_session, "admin_z", "pass", is_admin=True)
    user = create_user(db_session, "user_z", "pass", is_admin=False)
    project = create_project(db_session, name="proj_z")
    room = create_chat_room(db_session, project.id, name="room_z")

    admin_headers = auth_headers(client, "admin_z", "pass")
    user_headers = auth_headers(client, "user_z", "pass")

    # Unassigned user cannot list rooms
    response = client.get(f"/projects/{project.id}/chat-rooms", headers=user_headers)
    assert response.status_code == 403

    # Assign user then access
    response = client.post(f"/projects/{project.id}/assign/{user.id}", headers=admin_headers)
    assert response.status_code == 204

    response = client.get(f"/projects/{project.id}/chat-rooms/{room.id}", headers=user_headers)
    assert response.status_code == 200

    # Non-admin cannot assign
    response = client.post(f"/projects/{project.id}/assign/{user.id}", headers=user_headers)
    assert response.status_code == 403

    # Chat room not found
    response = client.get(f"/projects/{project.id}/chat-rooms/999", headers=user_headers)
    assert response.status_code == 404

    # Messages room not found
    response = client.get(f"/projects/{project.id}/chat-rooms/999/messages", headers=user_headers)
    assert response.status_code == 404


def test_chat_room_annotations_access(client, db_session):
    admin = create_user(db_session, "admin_y", "pass", is_admin=True)
    user = create_user(db_session, "user_y", "pass", is_admin=False)
    project = create_project(db_session, name="proj_y")
    room = create_chat_room(db_session, project.id, name="room_y")
    msg = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")
    assign_user(db_session, user.id, project.id)
    create_annotation(db_session, msg.id, user.id, project.id, thread_id="T1")

    admin_headers = auth_headers(client, "admin_y", "pass")
    user_headers = auth_headers(client, "user_y", "pass")

    response = client.get(f"/projects/{project.id}/chat-rooms/{room.id}/annotations", headers=user_headers)
    assert response.status_code == 200
    response = client.get(f"/projects/{project.id}/chat-rooms/{room.id}/annotations", headers=admin_headers)
    assert response.status_code == 200


def test_admin_missing_resources(client, db_session):
    admin = create_user(db_session, "admin_m", "pass", is_admin=True)
    headers = auth_headers(client, "admin_m", "pass")

    response = client.delete("/admin/projects/999", headers=headers)
    assert response.status_code == 404

    response = client.delete("/admin/users/999", headers=headers)
    assert response.status_code == 404

    response = client.get("/admin/chat-rooms/999/aggregated-annotations", headers=headers)
    assert response.status_code == 404


def test_crud_misc(db_session):
    user = create_user(db_session, "user_misc", "pass", is_admin=False)
    project = create_project(db_session, name="proj_misc")
    room = create_chat_room(db_session, project.id, name="room_misc")
    assign_user(db_session, user.id, project.id)

    assert crud.get_users(db_session)
    assert crud.get_user_by_username(db_session, "user_misc").id == user.id
    assert crud.get_project(db_session, project.id).id == project.id
    assert crud.get_chat_room(db_session, room.id).id == room.id

    # Update project
    from app.schemas import ProjectUpdate
    updated = crud.update_project(db_session, project, ProjectUpdate(name="proj_misc2"))
    assert updated.name == "proj_misc2"

    # Get chat rooms by project
    rooms = crud.get_chat_rooms_by_project(db_session, project.id)
    assert len(rooms) == 1


def test_database_get_db():
    gen = database.get_db()
    db = next(gen)
    assert db is not None
    try:
        gen.close()
    except Exception:
        pass
