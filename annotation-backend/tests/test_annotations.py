from conftest import (
    create_user,
    create_project,
    create_chat_room,
    create_message,
    assign_user,
    auth_headers,
    create_annotation
)


def test_create_and_delete_annotation(client, db_session):
    admin = create_user(db_session, "admin_a", "pass", is_admin=True)
    user = create_user(db_session, "user_a", "pass", is_admin=False)
    project = create_project(db_session, name="projA")
    room = create_chat_room(db_session, project.id, name="roomA")
    msg = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")
    assign_user(db_session, user.id, project.id)

    user_headers = auth_headers(client, "user_a", "pass")

    # Create annotation
    response = client.post(
        f"/projects/{project.id}/messages/{msg.id}/annotations/",
        json={"message_id": msg.id, "thread_id": "T0"},
        headers=user_headers
    )
    assert response.status_code == 200
    annotation_id = response.json()["id"]

    # Duplicate annotation should fail
    response = client.post(
        f"/projects/{project.id}/messages/{msg.id}/annotations/",
        json={"message_id": msg.id, "thread_id": "T0"},
        headers=user_headers
    )
    assert response.status_code == 400

    # Delete annotation as owner
    response = client.delete(
        f"/projects/{project.id}/messages/{msg.id}/annotations/{annotation_id}",
        headers=user_headers
    )
    assert response.status_code == 204


def test_get_message_annotations_admin_vs_user(client, db_session):
    admin = create_user(db_session, "admin_b", "pass", is_admin=True)
    user = create_user(db_session, "user_b", "pass", is_admin=False)
    project = create_project(db_session, name="projB")
    room = create_chat_room(db_session, project.id, name="roomB")
    msg = create_message(db_session, room.id, turn_id="T2", user_id="u1", text="hello")
    assign_user(db_session, user.id, project.id)
    assign_user(db_session, admin.id, project.id)

    create_annotation(db_session, msg.id, user.id, project.id, thread_id="T1")

    admin_headers = auth_headers(client, "admin_b", "pass")
    user_headers = auth_headers(client, "user_b", "pass")

    response = client.get(
        f"/projects/{project.id}/messages/{msg.id}/annotations/",
        headers=user_headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get(
        f"/projects/{project.id}/messages/{msg.id}/annotations/",
        headers=admin_headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_my_annotations(client, db_session):
    user = create_user(db_session, "user_c", "pass", is_admin=False)
    project = create_project(db_session, name="projC")
    room = create_chat_room(db_session, project.id, name="roomC")
    msg = create_message(db_session, room.id, turn_id="T3", user_id="u1", text="hello")
    assign_user(db_session, user.id, project.id)
    create_annotation(db_session, msg.id, user.id, project.id, thread_id="T2")

    headers = auth_headers(client, "user_c", "pass")
    response = client.get(f"/projects/{project.id}/annotations/my", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["message_turn_id"] == "T3"
