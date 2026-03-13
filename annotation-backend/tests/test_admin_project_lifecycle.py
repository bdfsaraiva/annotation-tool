import pytest

from app import crud
from app.schemas import ProjectUpdate
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


def test_admin_project_lifecycle(client, db_session):
    admin = create_user(db_session, "admin_life", "pass", is_admin=True)
    headers = auth_headers(client, "admin_life", "pass")

    # Create project
    response = client.post("/admin/projects", json={"name": "life", "annotation_type": "disentanglement"}, headers=headers)
    assert response.status_code == 200
    project_id = response.json()["id"]

    # Get project
    response = client.get(f"/admin/projects/{project_id}", headers=headers)
    assert response.status_code == 200

    # Update project
    response = client.put(f"/admin/projects/{project_id}", json={"description": "updated"}, headers=headers)
    assert response.status_code == 200

    # List projects
    response = client.get("/admin/projects", headers=headers)
    assert response.status_code == 200

    # Delete project
    response = client.delete(f"/admin/projects/{project_id}", headers=headers)
    assert response.status_code == 204


def test_crud_annotation_import_branches(db_session):
    user = create_user(db_session, "user_imp2", "pass", is_admin=False)
    project = create_project(db_session, name="proj_imp2")
    room = create_chat_room(db_session, project.id, name="room_imp2")
    msg = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")

    # Missing turn_id / thread_id
    imported, skipped, errors = crud.import_annotations_for_chat_room(
        db=db_session,
        chat_room_id=room.id,
        annotator_id=user.id,
        project_id=project.id,
        annotations_data=[{"turn_id": "", "thread_id": ""}]
    )
    assert skipped == 1

    # Missing message
    imported, skipped, errors = crud.import_annotations_for_chat_room(
        db=db_session,
        chat_room_id=room.id,
        annotator_id=user.id,
        project_id=project.id,
        annotations_data=[{"turn_id": "T2", "thread_id": "X"}]
    )
    assert skipped == 1

    # Existing annotation update
    create_annotation(db_session, msg.id, user.id, project.id, thread_id="A")
    imported, skipped, errors = crud.import_annotations_for_chat_room(
        db=db_session,
        chat_room_id=room.id,
        annotator_id=user.id,
        project_id=project.id,
        annotations_data=[{"turn_id": "T1", "thread_id": "B"}]
    )
    assert imported == 1


def test_crud_annotation_queries(db_session):
    user = create_user(db_session, "user_q2", "pass", is_admin=False)
    admin = create_user(db_session, "admin_q2", "pass", is_admin=True)
    project = create_project(db_session, name="proj_q2")
    room = create_chat_room(db_session, project.id, name="room_q2")
    msg = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")
    create_annotation(db_session, msg.id, user.id, project.id, thread_id="T1")

    all_ann = crud.get_annotations_for_chat_room(db_session, room.id)
    by_annot = crud.get_annotations_for_chat_room_by_annotator(db_session, room.id, user.id)
    admin_all = crud.get_all_annotations_for_chat_room_admin(db_session, room.id)
    assert len(all_ann) == len(by_annot) == len(admin_all) == 1


def test_crud_pairs_queries(db_session):
    user = create_user(db_session, "user_pairq", "pass", is_admin=False)
    project = create_project(db_session, name="proj_pairq", annotation_type="adjacency_pairs", relation_types=["rel"])
    room = create_chat_room(db_session, project.id, name="room_pairq")
    msg1 = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")
    msg2 = create_message(db_session, room.id, turn_id="T2", user_id="u2", text="hi")
    create_pair(db_session, msg1.id, msg2.id, user.id, project.id, relation_type="rel")

    pairs = crud.get_adjacency_pairs_for_chat_room_by_annotator(db_session, room.id, user.id)
    admin_pairs = crud.get_all_adjacency_pairs_for_chat_room_admin(db_session, room.id)
    assert len(pairs) == 1
    assert len(admin_pairs) == 1
