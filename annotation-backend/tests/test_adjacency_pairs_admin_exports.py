import json

import pytest

from conftest import (
    create_user,
    create_project,
    create_chat_room,
    create_message,
    assign_user,
    auth_headers
)


def test_adjacency_pairs_error_branches(client, db_session):
    user = create_user(db_session, "user_ap", "pass", is_admin=False)
    project = create_project(db_session, name="proj_ap", annotation_type="adjacency_pairs", relation_types=["rel"])
    room = create_chat_room(db_session, project.id, name="room_ap")
    msg = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")
    assign_user(db_session, user.id, project.id)
    headers = auth_headers(client, "user_ap", "pass")

    # Missing project
    response = client.get(f"/projects/999/chat-rooms/{room.id}/adjacency-pairs/", headers=headers)
    assert response.status_code in [403, 404]

    # Missing chat room
    response = client.get(f"/projects/{project.id}/chat-rooms/999/adjacency-pairs/", headers=headers)
    assert response.status_code == 404

    # No relation types configured
    project.relation_types = []
    db_session.commit()
    response = client.post(
        f"/projects/{project.id}/chat-rooms/{room.id}/adjacency-pairs/",
        json={"from_message_id": msg.id, "to_message_id": msg.id, "relation_type": "rel"},
        headers=headers
    )
    assert response.status_code in [400, 404]

    # Restore relation types and test self-link
    project.relation_types = ["rel"]
    db_session.commit()
    response = client.post(
        f"/projects/{project.id}/chat-rooms/{room.id}/adjacency-pairs/",
        json={"from_message_id": msg.id, "to_message_id": msg.id, "relation_type": "rel"},
        headers=headers
    )
    assert response.status_code == 400


def test_admin_export_adjacency_errors(client, db_session):
    admin = create_user(db_session, "admin_ea", "pass", is_admin=True)
    project = create_project(db_session, name="proj_ea", annotation_type="disentanglement")
    room = create_chat_room(db_session, project.id, name="room_ea")
    headers = auth_headers(client, "admin_ea", "pass")

    # Project not adjacency pairs
    response = client.get(f"/admin/chat-rooms/{room.id}/export-adjacency-pairs", headers=headers)
    assert response.status_code == 400

    # Missing chat room
    response = client.get("/admin/chat-rooms/999/export-adjacency-pairs", headers=headers)
    assert response.status_code == 404

    # Adjacency project but no assigned users -> 404
    adj_project = create_project(db_session, name="proj_ea2", annotation_type="adjacency_pairs", relation_types=["rel"])
    adj_room = create_chat_room(db_session, adj_project.id, name="room_ea2")
    response = client.get(f"/admin/chat-rooms/{adj_room.id}/export-adjacency-pairs", headers=headers)
    assert response.status_code == 404

    # Annotator not found
    response = client.get(f"/admin/chat-rooms/{adj_room.id}/export-adjacency-pairs?annotator_id=999", headers=headers)
    assert response.status_code == 404
