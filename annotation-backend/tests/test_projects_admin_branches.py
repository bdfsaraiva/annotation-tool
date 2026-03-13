import json
import pytest

from app import crud
from app.utils import csv_utils
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


def test_projects_additional_endpoints(client, db_session):
    admin = create_user(db_session, "admin_p4", "pass", is_admin=True)
    user = create_user(db_session, "user_p4", "pass", is_admin=False)
    project = create_project(db_session, name="proj_p4")
    room = create_chat_room(db_session, project.id, name="room_p4")
    assign_user(db_session, user.id, project.id)

    admin_headers = auth_headers(client, "admin_p4", "pass")
    user_headers = auth_headers(client, "user_p4", "pass")

    # Get project users
    response = client.get(f"/projects/{project.id}/users", headers=user_headers)
    assert response.status_code == 200

    # Unauthorized get project users
    other = create_user(db_session, "user_p4b", "pass", is_admin=False)
    other_headers = auth_headers(client, "user_p4b", "pass")
    response = client.get(f"/projects/{project.id}/users", headers=other_headers)
    assert response.status_code == 403

    # Project not found
    response = client.get("/projects/999", headers=admin_headers)
    assert response.status_code == 404

    # Chat room annotations missing room
    response = client.get(f"/projects/{project.id}/chat-rooms/999/annotations", headers=user_headers)
    assert response.status_code == 404

    # Admin access should pass verify_project_access without assignment
    admin_headers = auth_headers(client, "admin_p4", "pass")
    response = client.get(f"/projects/{project.id}/chat-rooms/{room.id}/annotations", headers=admin_headers)
    assert response.status_code == 200

    # Invalid token should be rejected (dependency coverage)
    response = client.get(
        f"/projects/{project.id}/chat-rooms/{room.id}/annotations",
        headers={"Authorization": "Bearer badtoken"}
    )
    assert response.status_code == 401


def test_admin_additional_branches(client, db_session, tmp_path):
    admin = create_user(db_session, "admin_p5", "pass", is_admin=True)
    headers = auth_headers(client, "admin_p5", "pass")

    # Duplicate user create
    client.post("/admin/users", json={"username": "dupuser", "password": "pass", "is_admin": False}, headers=headers)
    response = client.post("/admin/users", json={"username": "dupuser", "password": "pass", "is_admin": False}, headers=headers)
    assert response.status_code == 400

    # Update project with empty relation types
    project = create_project(db_session, name="proj_p5", annotation_type="adjacency_pairs", relation_types=["rel"])
    response = client.put(f"/admin/projects/{project.id}", json={"relation_types": []}, headers=headers)
    assert response.status_code == 400

    # Import annotations invalid file
    response = client.post(
        "/admin/chat-rooms/999/import-annotations",
        data={"user_id": 1},
        files={"file": ("bad.txt", b"x", "text/plain")},
        headers=headers
    )
    assert response.status_code in [400, 404]

    # Batch import invalid JSON
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{bad}", encoding="utf-8")
    response = client.post(
        "/admin/chat-rooms/999/import-batch-annotations",
        files={"file": ("bad.json", bad_json.read_bytes(), "application/json")},
        headers=headers
    )
    assert response.status_code in [400, 404]


def test_crud_error_branches(db_session):
    # IAA errors: missing chat room
    with pytest.raises(Exception):
        crud.get_chat_room_iaa_analysis(db_session, chat_room_id=999)

    project = create_project(db_session, name="proj_p6")
    room = create_chat_room(db_session, project.id, name="room_p6")
    # No messages -> error
    with pytest.raises(Exception):
        crud.get_chat_room_iaa_analysis(db_session, chat_room_id=room.id)

    # import_batch_annotations_for_chat_room errors
    from app.schemas import BatchAnnotationImport, BatchMetadata, BatchAnnotator, BatchAnnotationItem
    batch = BatchAnnotationImport(
        batch_metadata=BatchMetadata(project_id=project.id, chat_room_id=room.id, import_timestamp="2026-03-13T00:00:00"),
        annotators=[
            BatchAnnotator(annotator_username="abc", annotator_name="A", annotations=[BatchAnnotationItem(turn_id="T1", thread_id="X")])
        ]
    )
    # Chat room missing
    response = crud.import_batch_annotations_for_chat_room(db_session, chat_room_id=999, project_id=project.id, batch_data=batch)
    assert response.total_imported == 0


def test_csv_utils_error_branches(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(Exception):
        csv_utils.validate_csv_format(str(empty))

    bad = tmp_path / "bad.csv"
    bad.write_text("turn_id,user_id\n1,2\n", encoding="utf-8")
    with pytest.raises(Exception):
        csv_utils.import_chat_messages(str(bad))
