from conftest import (
    create_user,
    create_project,
    create_chat_room,
    create_message,
    assign_user,
    create_annotation,
    auth_headers
)


def test_annotations_error_branches(client, db_session):
    admin = create_user(db_session, "admin_ann_err", "pass", is_admin=True)
    user = create_user(db_session, "user_ann_err", "pass", is_admin=False)
    other = create_user(db_session, "user_ann_err2", "pass", is_admin=False)
    project = create_project(db_session, name="proj_ann_err")
    room = create_chat_room(db_session, project.id, name="room_ann_err")
    msg = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")
    assign_user(db_session, user.id, project.id)
    assign_user(db_session, other.id, project.id)

    headers_user = auth_headers(client, "user_ann_err", "pass")
    headers_other = auth_headers(client, "user_ann_err2", "pass")

    # Get annotations for missing message
    response = client.get(f"/projects/{project.id}/messages/999/annotations/", headers=headers_user)
    assert response.status_code == 404

    # Create annotation for missing message
    response = client.post(
        f"/projects/{project.id}/messages/999/annotations/",
        json={"message_id": 999, "thread_id": "T1"},
        headers=headers_user
    )
    assert response.status_code == 404

    # Delete annotation not found
    response = client.delete(
        f"/projects/{project.id}/messages/{msg.id}/annotations/999",
        headers=headers_user
    )
    assert response.status_code == 404

    # Delete annotation with missing message
    response = client.delete(
        f"/projects/{project.id}/messages/999/annotations/1",
        headers=headers_user
    )
    assert response.status_code == 404

    # Delete annotation without permission
    ann = create_annotation(db_session, msg.id, user.id, project.id, thread_id="A")
    response = client.delete(
        f"/projects/{project.id}/messages/{msg.id}/annotations/{ann.id}",
        headers=headers_other
    )
    assert response.status_code == 403
