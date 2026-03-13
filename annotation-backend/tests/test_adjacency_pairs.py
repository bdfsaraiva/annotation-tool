from conftest import (
    create_user,
    create_project,
    create_chat_room,
    create_message,
    assign_user,
    auth_headers
)


def test_adjacency_pairs_flow(client, db_session):
    admin = create_user(db_session, "admin_p", "pass", is_admin=True)
    user = create_user(db_session, "user_p", "pass", is_admin=False)
    project = create_project(
        db_session,
        name="projP",
        annotation_type="adjacency_pairs",
        relation_types=["question", "answer"]
    )
    room = create_chat_room(db_session, project.id, name="roomP")
    msg1 = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hi")
    msg2 = create_message(db_session, room.id, turn_id="T2", user_id="u2", text="yo")
    assign_user(db_session, user.id, project.id)

    headers = auth_headers(client, "user_p", "pass")

    # Create pair
    response = client.post(
        f"/projects/{project.id}/chat-rooms/{room.id}/adjacency-pairs/",
        json={"from_message_id": msg1.id, "to_message_id": msg2.id, "relation_type": "question"},
        headers=headers
    )
    assert response.status_code == 200
    pair_id = response.json()["id"]

    # Update pair relation type
    response = client.post(
        f"/projects/{project.id}/chat-rooms/{room.id}/adjacency-pairs/",
        json={"from_message_id": msg1.id, "to_message_id": msg2.id, "relation_type": "answer"},
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["relation_type"] == "answer"

    # List pairs
    response = client.get(
        f"/projects/{project.id}/chat-rooms/{room.id}/adjacency-pairs/",
        headers=headers
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Delete pair
    response = client.delete(
        f"/projects/{project.id}/chat-rooms/{room.id}/adjacency-pairs/{pair_id}",
        headers=headers
    )
    assert response.status_code == 204


def test_adjacency_pairs_invalid_type(client, db_session):
    user = create_user(db_session, "user_q", "pass", is_admin=False)
    project = create_project(db_session, name="projQ", annotation_type="adjacency_pairs", relation_types=["rel"])
    room = create_chat_room(db_session, project.id, name="roomQ")
    msg1 = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hi")
    msg2 = create_message(db_session, room.id, turn_id="T2", user_id="u2", text="yo")
    assign_user(db_session, user.id, project.id)

    headers = auth_headers(client, "user_q", "pass")
    response = client.post(
        f"/projects/{project.id}/chat-rooms/{room.id}/adjacency-pairs/",
        json={"from_message_id": msg1.id, "to_message_id": msg2.id, "relation_type": "bad"},
        headers=headers
    )
    assert response.status_code == 400


def test_adjacency_pairs_wrong_project_mode(client, db_session):
    user = create_user(db_session, "user_r", "pass", is_admin=False)
    project = create_project(db_session, name="projR", annotation_type="disentanglement")
    room = create_chat_room(db_session, project.id, name="roomR")
    msg1 = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hi")
    msg2 = create_message(db_session, room.id, turn_id="T2", user_id="u2", text="yo")
    assign_user(db_session, user.id, project.id)

    headers = auth_headers(client, "user_r", "pass")
    response = client.post(
        f"/projects/{project.id}/chat-rooms/{room.id}/adjacency-pairs/",
        json={"from_message_id": msg1.id, "to_message_id": msg2.id, "relation_type": "rel"},
        headers=headers
    )
    assert response.status_code == 400
