from conftest import (
    create_user,
    create_project,
    create_chat_room,
    create_message,
    assign_user,
    create_pair,
    auth_headers
)


def test_adjacency_pairs_admin_list_and_project_not_found(client, db_session):
    admin = create_user(db_session, "admin_ap2", "pass", is_admin=True)
    project = create_project(db_session, name="proj_ap2", annotation_type="adjacency_pairs", relation_types=["rel"])
    room = create_chat_room(db_session, project.id, name="room_ap2")
    headers = auth_headers(client, "admin_ap2", "pass")

    # Admin list (empty)
    response = client.get(f"/projects/{project.id}/chat-rooms/{room.id}/adjacency-pairs/", headers=headers)
    assert response.status_code == 200

    # Project not found
    response = client.get("/projects/999/chat-rooms/1/adjacency-pairs/", headers=headers)
    assert response.status_code == 404


def test_adjacency_pairs_create_missing_message_and_project(client, db_session):
    admin = create_user(db_session, "admin_ap3", "pass", is_admin=True)
    project = create_project(db_session, name="proj_ap3", annotation_type="adjacency_pairs", relation_types=["rel"])
    room = create_chat_room(db_session, project.id, name="room_ap3")
    headers = auth_headers(client, "admin_ap3", "pass")

    # Missing project (admin bypasses access check)
    response = client.post(
        "/projects/999/chat-rooms/1/adjacency-pairs/",
        json={"from_message_id": 1, "to_message_id": 2, "relation_type": "rel"},
        headers=headers
    )
    assert response.status_code == 404

    # Missing message
    response = client.post(
        f"/projects/{project.id}/chat-rooms/{room.id}/adjacency-pairs/",
        json={"from_message_id": 999, "to_message_id": 998, "relation_type": "rel"},
        headers=headers
    )
    assert response.status_code == 404


def test_adjacency_pairs_delete_errors(client, db_session):
    user = create_user(db_session, "user_ap3", "pass", is_admin=False)
    other = create_user(db_session, "user_ap3b", "pass", is_admin=False)
    admin = create_user(db_session, "admin_ap4", "pass", is_admin=True)
    project = create_project(db_session, name="proj_ap4", annotation_type="adjacency_pairs", relation_types=["rel"])
    room = create_chat_room(db_session, project.id, name="room_ap4")
    msg1 = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")
    msg2 = create_message(db_session, room.id, turn_id="T2", user_id="u2", text="hi")
    assign_user(db_session, user.id, project.id)
    assign_user(db_session, other.id, project.id)
    pair = create_pair(db_session, msg1.id, msg2.id, user.id, project.id, relation_type="rel")
    headers_user = auth_headers(client, "user_ap3", "pass")
    headers_other = auth_headers(client, "user_ap3b", "pass")
    headers_admin = auth_headers(client, "admin_ap4", "pass")

    # Pair not found
    response = client.delete(f"/projects/{project.id}/chat-rooms/{room.id}/adjacency-pairs/999", headers=headers_user)
    assert response.status_code == 404

    # Wrong project id
    response = client.delete(f"/projects/999/chat-rooms/{room.id}/adjacency-pairs/{pair.id}", headers=headers_admin)
    assert response.status_code == 404

    # Missing messages in this chat room (wrong room_id)
    other_room = create_chat_room(db_session, project.id, name="room_ap4b")
    response = client.delete(f"/projects/{project.id}/chat-rooms/{other_room.id}/adjacency-pairs/{pair.id}", headers=headers_admin)
    assert response.status_code == 404

    # Permission check
    response = client.delete(f"/projects/{project.id}/chat-rooms/{room.id}/adjacency-pairs/{pair.id}", headers=headers_other)
    assert response.status_code == 403
