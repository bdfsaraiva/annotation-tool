import io
import json

from conftest import (
    create_user,
    create_project,
    create_chat_room,
    create_message,
    assign_user,
    create_annotation,
    create_pair,
    auth_headers
)


def test_admin_user_crud(client, db_session):
    admin = create_user(db_session, "admin_u", "pass", is_admin=True)
    headers = auth_headers(client, "admin_u", "pass")

    # Create user
    response = client.post("/admin/users", json={"username": "newuser", "password": "pass", "is_admin": False}, headers=headers)
    assert response.status_code == 200
    user_id = response.json()["id"]

    # Update user
    response = client.put(f"/admin/users/{user_id}", json={"username": "newuser2"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "newuser2"

    # List users
    response = client.get("/admin/users", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 2

    # Delete user
    response = client.delete(f"/admin/users/{user_id}", headers=headers)
    assert response.status_code == 204

    # Prevent deleting self
    response = client.delete(f"/admin/users/{admin.id}", headers=headers)
    assert response.status_code == 400


def test_import_chat_room_csv_and_delete(client, db_session, tmp_path):
    admin = create_user(db_session, "admin_csv", "pass", is_admin=True)
    project = create_project(db_session, name="proj_csv")
    headers = auth_headers(client, "admin_csv", "pass")

    csv_content = "turn_id,user_id,turn_text,reply_to_turn\n1,10,hello,\n2,11,world,99\n"
    file_path = tmp_path / "room.csv"
    file_path.write_text(csv_content, encoding="utf-8")

    with open(file_path, "rb") as f:
        response = client.post(
            f"/admin/projects/{project.id}/import-chat-room-csv",
            files={"file": ("room.csv", f, "text/csv")},
            headers=headers
        )
    assert response.status_code == 200
    payload = response.json()
    room_id = payload["chat_room"]["id"]
    assert payload["import_details"]["warnings"]

    # Delete chat room
    response = client.delete(f"/admin/chat-rooms/{room_id}", headers=headers)
    assert response.status_code == 204


def test_import_annotations_csv(client, db_session, tmp_path):
    admin = create_user(db_session, "admin_imp", "pass", is_admin=True)
    user = create_user(db_session, "user_imp", "pass", is_admin=False)
    project = create_project(db_session, name="proj_imp")
    room = create_chat_room(db_session, project.id, name="room_imp")
    msg = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")

    headers = auth_headers(client, "admin_imp", "pass")
    csv_content = "turn_id,thread_id\nT1,TH1\n"
    file_path = tmp_path / "ann.csv"
    file_path.write_text(csv_content, encoding="utf-8")

    with open(file_path, "rb") as f:
        response = client.post(
            f"/admin/chat-rooms/{room.id}/import-annotations",
            data={"user_id": user.id},
            files={"file": ("ann.csv", f, "text/csv")},
            headers=headers
        )
    assert response.status_code == 200
    assert response.json()["imported_count"] == 1


def test_aggregated_export_and_iaa(client, db_session):
    admin = create_user(db_session, "admin_ag", "pass", is_admin=True)
    user1 = create_user(db_session, "user_ag1", "pass", is_admin=False)
    user2 = create_user(db_session, "user_ag2", "pass", is_admin=False)
    project = create_project(db_session, name="proj_ag")
    room = create_chat_room(db_session, project.id, name="room_ag")
    msg1 = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")
    msg2 = create_message(db_session, room.id, turn_id="T2", user_id="u2", text="hi")
    assign_user(db_session, user1.id, project.id)
    assign_user(db_session, user2.id, project.id)

    create_annotation(db_session, msg1.id, user1.id, project.id, thread_id="A")
    create_annotation(db_session, msg2.id, user1.id, project.id, thread_id="B")
    create_annotation(db_session, msg1.id, user2.id, project.id, thread_id="A")
    create_annotation(db_session, msg2.id, user2.id, project.id, thread_id="B")

    headers = auth_headers(client, "admin_ag", "pass")

    response = client.get(f"/admin/chat-rooms/{room.id}/aggregated-annotations", headers=headers)
    assert response.status_code == 200
    assert response.json()["total_messages"] == 2

    response = client.get(f"/admin/chat-rooms/{room.id}/iaa", headers=headers)
    assert response.status_code == 200
    assert response.json()["analysis_status"] in ["Complete", "Partial"]

    response = client.get(f"/admin/chat-rooms/{room.id}/export", headers=headers)
    assert response.status_code == 200
    assert "Content-Disposition" in response.headers


def test_batch_import_and_export_adjacency_pairs(client, db_session, tmp_path):
    admin = create_user(db_session, "admin_ba", "pass", is_admin=True)
    project = create_project(
        db_session, name="proj_ba", annotation_type="adjacency_pairs", relation_types=["rel"]
    )
    room = create_chat_room(db_session, project.id, name="room_ba")
    msg1 = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")
    msg2 = create_message(db_session, room.id, turn_id="T2", user_id="u2", text="hi")
    assign_user(db_session, admin.id, project.id)

    headers = auth_headers(client, "admin_ba", "pass")

    # Batch import
    batch_payload = {
        "batch_metadata": {
            "project_id": project.id,
            "chat_room_id": room.id,
            "import_timestamp": "2026-03-13T00:00:00"
        },
        "annotators": [
            {
                "annotator_username": "annot1",
                "annotator_name": "Annotator One",
                "annotations": [
                    {"turn_id": "T1", "thread_id": "X"},
                    {"turn_id": "T2", "thread_id": "Y"}
                ]
            }
        ]
    }
    json_path = tmp_path / "batch.json"
    json_path.write_text(json.dumps(batch_payload), encoding="utf-8")

    with open(json_path, "rb") as f:
        response = client.post(
            f"/admin/chat-rooms/{room.id}/import-batch-annotations",
            files={"file": ("batch.json", f, "application/json")},
            headers=headers
        )
    assert response.status_code == 200

    # Create adjacency pair for export
    user = db_session.query(type(admin)).filter_by(username="annot1").first()
    create_pair(db_session, msg1.id, msg2.id, user.id, project.id, relation_type="rel")

    # Export for a single annotator
    response = client.get(f"/admin/chat-rooms/{room.id}/export-adjacency-pairs?annotator_id={user.id}", headers=headers)
    assert response.status_code == 200
    assert response.headers["Content-Disposition"].endswith(".txt")

    # Export all annotators (zip)
    response = client.get(f"/admin/chat-rooms/{room.id}/export-adjacency-pairs", headers=headers)
    assert response.status_code == 200
    assert response.headers["Content-Disposition"].endswith(".zip")
