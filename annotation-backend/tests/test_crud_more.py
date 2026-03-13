import pytest

from app import crud
from app.schemas import UserCreate, UserUpdate, ProjectUpdate
from conftest import (
    create_user,
    create_project,
    create_chat_room,
    create_message,
    assign_user,
    create_annotation,
    create_pair
)


def test_crud_user_and_project_operations(db_session):
    # create_user via crud
    user = crud.create_user(db_session, UserCreate(username="crud_user", password="pass", is_admin=False), "hashed")
    assert user.username == "crud_user"

    # update_user
    updated = crud.update_user(db_session, user, UserUpdate(username="crud_user2"))
    assert updated.username == "crud_user2"

    # get_user/get_users
    assert crud.get_user(db_session, user.id).id == user.id
    assert len(crud.get_users(db_session)) >= 1

    # delete_user
    crud.delete_user(db_session, user)

    # project operations
    project = create_project(db_session, name="crud_proj")
    updated_project = crud.update_project(db_session, project, ProjectUpdate(description="x"))
    assert updated_project.description == "x"
    assert crud.get_project(db_session, project.id).id == project.id
    assert len(crud.get_projects(db_session)) >= 1

    # delete_project
    crud.delete_project(db_session, project)


def test_crud_chat_room_and_messages(db_session):
    project = create_project(db_session, name="crud_proj2")
    room = create_chat_room(db_session, project.id, name="crud_room")
    msg = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")

    assert crud.get_chat_room(db_session, room.id).id == room.id
    assert len(crud.get_chat_rooms_by_project(db_session, project.id)) == 1
    assert crud.get_chat_message(db_session, msg.id).id == msg.id
    assert crud.get_chat_message_by_turn_id(db_session, room.id, "T1").id == msg.id
    assert len(crud.get_chat_messages_by_room(db_session, room.id)) == 1

    crud.delete_chat_room(db_session, room)


def test_crud_annotations_and_pairs(db_session):
    user = create_user(db_session, "crud_ann_user", "pass", is_admin=False)
    project = create_project(db_session, name="crud_ann_proj", annotation_type="adjacency_pairs", relation_types=["rel"])
    room = create_chat_room(db_session, project.id, name="crud_ann_room")
    msg1 = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")
    msg2 = create_message(db_session, room.id, turn_id="T2", user_id="u2", text="hi")

    ann = create_annotation(db_session, msg1.id, user.id, project.id, thread_id="A")
    assert crud.get_annotation(db_session, ann.id).id == ann.id
    assert len(crud.get_annotations_by_message(db_session, msg1.id)) == 1
    assert len(crud.get_annotations_by_annotator(db_session, user.id)) == 1

    pair = create_pair(db_session, msg1.id, msg2.id, user.id, project.id, relation_type="rel")
    assert crud.get_adjacency_pair(db_session, pair.id).id == pair.id

    assert crud.get_project_assignment(db_session, assign_user(db_session, user.id, project.id).id)
    assert len(crud.get_project_assignments_by_user(db_session, user.id)) >= 1
    assert len(crud.get_project_assignments_by_project(db_session, project.id)) >= 1


def test_crud_create_annotation_and_completion_update(db_session):
    user = create_user(db_session, "crud_ann2", "pass", is_admin=False)
    project = create_project(db_session, name="crud_ann2_proj")
    room = create_chat_room(db_session, project.id, name="crud_ann2_room")
    msg = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")

    class DummyAnnotation:
        def __init__(self, message_id, annotator_id, project_id, thread_id):
            self.message_id = message_id
            self.annotator_id = annotator_id
            self.project_id = project_id
            self.thread_id = thread_id

    ann = crud.create_annotation(
        db_session,
        DummyAnnotation(
            message_id=msg.id,
            annotator_id=user.id,
            project_id=project.id,
            thread_id="T1"
        ),
        annotator_id=user.id,
        project_id=project.id
    )
    assert ann.id is not None

    # Upsert completion (create then update path)
    completion = crud.upsert_chat_room_completion(db_session, room.id, project.id, user.id, True)
    completion2 = crud.upsert_chat_room_completion(db_session, room.id, project.id, user.id, False)
    assert completion2.is_completed is False

    # Completion summary error branch
    try:
        crud.get_chat_room_completion_summary(db_session, chat_room_id=999)
    except Exception:
        pass

    # Adjacency status error branch
    try:
        crud.get_adjacency_pairs_status(db_session, chat_room_id=999)
    except Exception:
        pass


def test_crud_update_user_and_project_fields(db_session):
    user = create_user(db_session, "crud_update_user", "pass", is_admin=False)
    updated = crud.update_user(db_session, user, UserUpdate(is_admin=True))
    assert updated.is_admin is True

    project = create_project(db_session, name="crud_update_proj")
    updated_project = crud.update_project(
        db_session,
        project,
        ProjectUpdate(annotation_type="adjacency_pairs", relation_types=["rel1", "rel2"])
    )
    assert updated_project.annotation_type == "adjacency_pairs"
    assert updated_project.relation_types == ["rel1", "rel2"]


def test_crud_adjacency_pairs_status_started(db_session):
    user1 = create_user(db_session, "crud_ap_status1", "pass", is_admin=False)
    user2 = create_user(db_session, "crud_ap_status2", "pass", is_admin=False)
    project = create_project(db_session, name="crud_ap_status", annotation_type="adjacency_pairs", relation_types=["rel"])
    room = create_chat_room(db_session, project.id, name="crud_ap_status_room")
    msg1 = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")
    msg2 = create_message(db_session, room.id, turn_id="T2", user_id="u2", text="hi")
    assign_user(db_session, user1.id, project.id)
    assign_user(db_session, user2.id, project.id)
    create_pair(db_session, msg1.id, msg2.id, user1.id, project.id, relation_type="rel")

    status = crud.get_adjacency_pairs_status(db_session, chat_room_id=room.id)
    assert status.status == "Started"


def test_import_annotations_for_chat_room_exception(monkeypatch, db_session):
    user = create_user(db_session, "crud_ann_exc", "pass", is_admin=False)
    project = create_project(db_session, name="crud_ann_exc_proj")
    room = create_chat_room(db_session, project.id, name="crud_ann_exc_room")

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(crud, "get_chat_message_by_turn_id", boom)
    imported, skipped, errors = crud.import_annotations_for_chat_room(
        db=db_session,
        chat_room_id=room.id,
        annotator_id=user.id,
        project_id=project.id,
        annotations_data=[{"turn_id": "T1", "thread_id": "A"}]
    )
    assert imported == 0
    assert skipped == 1
    assert errors


def test_import_batch_annotations_project_mismatch(db_session):
    from app.schemas import BatchAnnotationImport, BatchMetadata, BatchAnnotator, BatchAnnotationItem

    project = create_project(db_session, name="crud_batch_proj")
    room = create_chat_room(db_session, project.id, name="crud_batch_room")

    batch = BatchAnnotationImport(
        batch_metadata=BatchMetadata(project_id=project.id, chat_room_id=room.id, import_timestamp="2026-03-13T00:00:00"),
        annotators=[
            BatchAnnotator(
                annotator_username="batch_user",
                annotator_name="Batch User",
                annotations=[BatchAnnotationItem(turn_id="T1", thread_id="X")]
            )
        ]
    )

    response = crud.import_batch_annotations_for_chat_room(
        db_session,
        chat_room_id=room.id,
        project_id=999,
        batch_data=batch
    )
    assert response.total_imported == 0


def test_import_batch_annotations_error_messages(monkeypatch, db_session):
    from app.schemas import BatchAnnotationImport, BatchMetadata, BatchAnnotator, BatchAnnotationItem

    project = create_project(db_session, name="crud_batch_proj2")
    room = create_chat_room(db_session, project.id, name="crud_batch_room2")
    ok_user = create_user(db_session, "batch_ok", "pass", is_admin=False)
    bad_user = create_user(db_session, "batch_bad", "pass", is_admin=False)

    batch = BatchAnnotationImport(
        batch_metadata=BatchMetadata(project_id=project.id, chat_room_id=room.id, import_timestamp="2026-03-13T00:00:00"),
        annotators=[
            BatchAnnotator(
                annotator_username="batch_ok",
                annotator_name="Batch Ok",
                annotations=[BatchAnnotationItem(turn_id="T1", thread_id="X")]
            ),
            BatchAnnotator(
                annotator_username="batch_bad",
                annotator_name="Batch Bad",
                annotations=[BatchAnnotationItem(turn_id="T2", thread_id="Y")]
            )
        ]
    )

    def fake_import(db, chat_room_id, annotator_id, project_id, annotations_data):
        if annotator_id == bad_user.id:
            raise RuntimeError("boom")
        return 1, 0, []

    monkeypatch.setattr(crud, "import_annotations_for_chat_room", fake_import)

    response = crud.import_batch_annotations_for_chat_room(
        db_session,
        chat_room_id=room.id,
        project_id=project.id,
        batch_data=batch
    )
    assert "Import completed with" in response.message


def test_import_batch_annotations_all_failed(monkeypatch, db_session):
    from app.schemas import BatchAnnotationImport, BatchMetadata, BatchAnnotator, BatchAnnotationItem

    project = create_project(db_session, name="crud_batch_proj3")
    room = create_chat_room(db_session, project.id, name="crud_batch_room3")

    batch = BatchAnnotationImport(
        batch_metadata=BatchMetadata(project_id=project.id, chat_room_id=room.id, import_timestamp="2026-03-13T00:00:00"),
        annotators=[
            BatchAnnotator(
                annotator_username="batch_fail",
                annotator_name="Batch Fail",
                annotations=[BatchAnnotationItem(turn_id="T1", thread_id="X")]
            )
        ]
    )

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(crud, "import_annotations_for_chat_room", boom)

    response = crud.import_batch_annotations_for_chat_room(
        db_session,
        chat_room_id=room.id,
        project_id=project.id,
        batch_data=batch
    )
    assert "No annotations were imported" in response.message


def test_calculate_one_to_one_accuracy_empty():
    assert crud._calculate_one_to_one_accuracy([], []) == 0.0


def test_chat_room_iaa_not_enough_data(db_session):
    user1 = create_user(db_session, "iaa_user1", "pass", is_admin=False)
    user2 = create_user(db_session, "iaa_user2", "pass", is_admin=False)
    project = create_project(db_session, name="iaa_proj")
    room = create_chat_room(db_session, project.id, name="iaa_room")
    msg1 = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")
    msg2 = create_message(db_session, room.id, turn_id="T2", user_id="u2", text="hi")
    assign_user(db_session, user1.id, project.id)
    assign_user(db_session, user2.id, project.id)

    create_annotation(db_session, msg1.id, user1.id, project.id, thread_id="A")

    iaa = crud.get_chat_room_iaa_analysis(db_session, chat_room_id=room.id)
    assert iaa.analysis_status == "NotEnoughData"
    assert len(iaa.pending_annotators) >= 1


def test_export_chat_room_data_missing(db_session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        crud.export_chat_room_data(db_session, chat_room_id=999)
