from app import models
from conftest import create_user, create_project, create_chat_room, create_message, assign_user, auth_headers


def test_project_assignment_and_listing(client, db_session):
    admin = create_user(db_session, "admin", "pass", is_admin=True)
    user = create_user(db_session, "usera", "pass", is_admin=False)
    other = create_user(db_session, "userb", "pass", is_admin=False)
    project = create_project(db_session, name="proj1")

    admin_headers = auth_headers(client, "admin", "pass")
    user_headers = auth_headers(client, "usera", "pass")
    other_headers = auth_headers(client, "userb", "pass")

    # Assign user to project
    response = client.post(f"/projects/{project.id}/assign/{user.id}", headers=admin_headers)
    assert response.status_code == 204

    # List projects for assigned user
    response = client.get("/projects/", headers=user_headers)
    assert response.status_code == 200
    assert len(response.json()["projects"]) == 1

    # Unassigned user cannot access project
    response = client.get(f"/projects/{project.id}", headers=other_headers)
    assert response.status_code == 403


def test_chat_room_messages_pagination(client, db_session):
    admin = create_user(db_session, "admin2", "pass", is_admin=True)
    project = create_project(db_session, name="proj2")
    room = create_chat_room(db_session, project.id, name="room1")
    for i in range(1, 6):
        create_message(db_session, room.id, turn_id=f"T{i}", user_id="u1", text=f"msg{i}")

    headers = auth_headers(client, "admin2", "pass")
    response = client.get(f"/projects/{project.id}/chat-rooms/{room.id}/messages", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 5
    assert len(payload["messages"]) == 5


def test_project_chat_rooms_access(client, db_session):
    admin = create_user(db_session, "admin3", "pass", is_admin=True)
    user = create_user(db_session, "userc", "pass", is_admin=False)
    project = create_project(db_session, name="proj3")
    room = create_chat_room(db_session, project.id, name="room2")
    assign_user(db_session, user.id, project.id)

    user_headers = auth_headers(client, "userc", "pass")
    response = client.get(f"/projects/{project.id}/chat-rooms", headers=user_headers)
    assert response.status_code == 200
    assert response.json()[0]["id"] == room.id
