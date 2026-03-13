import io

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
    create_pair
)


def test_csv_utils_validation(tmp_path):
    valid_csv = "turn_id,user_id,turn_text\n1,10,hello\n"
    valid_path = tmp_path / "valid.csv"
    valid_path.write_text(valid_csv, encoding="utf-8")
    assert csv_utils.validate_csv_format(str(valid_path))
    messages = csv_utils.import_chat_messages(str(valid_path))
    assert len(messages) == 1

    invalid_csv = "turn_id,user_id\n1,10\n"
    invalid_path = tmp_path / "invalid.csv"
    invalid_path.write_text(invalid_csv, encoding="utf-8")
    with pytest.raises(ValueError):
        csv_utils.validate_csv_format(str(invalid_path))

    # reply_to_turn and numeric user_id handling
    csv_with_reply = "turn_id,user_id,turn_text,reply_to_turn\n1,10.0,hello,2\n2,11,world,\n"
    reply_path = tmp_path / "reply.csv"
    reply_path.write_text(csv_with_reply, encoding="utf-8")
    messages = csv_utils.import_chat_messages(str(reply_path))
    assert messages[0]["reply_to_turn"] == "2.0"


def test_annotations_csv_utils(tmp_path):
    valid_csv = "turn_id,thread_id\nT1,TH1\n"
    valid_path = tmp_path / "ann.csv"
    valid_path.write_text(valid_csv, encoding="utf-8")
    assert csv_utils.validate_annotations_csv_format(str(valid_path))
    annotations = csv_utils.import_annotations_from_csv(str(valid_path))
    assert annotations[0]["turn_id"] == "T1"

    invalid_csv = "turn_id\nT1\n"
    invalid_path = tmp_path / "ann_invalid.csv"
    invalid_path.write_text(invalid_csv, encoding="utf-8")
    with pytest.raises(ValueError):
        csv_utils.validate_annotations_csv_format(str(invalid_path))

    # thread column name variants
    thread_csv = "turn_id,thread\nT2,TH2\n"
    thread_path = tmp_path / "thread.csv"
    thread_path.write_text(thread_csv, encoding="utf-8")
    annotations = csv_utils.import_annotations_from_csv(str(thread_path))
    assert annotations[0]["thread_id"] == "TH2"


def test_crud_completion_and_status(db_session):
    user = create_user(db_session, "user_c1", "pass", is_admin=False)
    project = create_project(db_session, name="proj_c1", annotation_type="adjacency_pairs", relation_types=["rel"])
    room = create_chat_room(db_session, project.id, name="room_c1")
    msg1 = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")
    msg2 = create_message(db_session, room.id, turn_id="T2", user_id="u2", text="hi")
    assign_user(db_session, user.id, project.id)

    # No completion yet
    summary = crud.get_chat_room_completion_summary(db_session, room.id)
    assert summary.completed_count == 0

    # Upsert completion
    crud.upsert_chat_room_completion(db_session, room.id, project.id, user.id, True)
    summary = crud.get_chat_room_completion_summary(db_session, room.id)
    assert summary.completed_count == 1

    status = crud.get_adjacency_pairs_status(db_session, room.id)
    assert status.status in ["Started", "Completed", "NotStarted"]

    # Add relation to move status to Started
    create_pair(db_session, msg1.id, msg2.id, user.id, project.id, relation_type="rel")
    status = crud.get_adjacency_pairs_status(db_session, room.id)
    assert status.status in ["Started", "Completed"]


def test_export_chat_room_data(db_session):
    user = create_user(db_session, "user_c2", "pass", is_admin=False)
    project = create_project(db_session, name="proj_c2")
    room = create_chat_room(db_session, project.id, name="room_c2")
    msg1 = create_message(db_session, room.id, turn_id="T1", user_id="u1", text="hello")
    assign_user(db_session, user.id, project.id)
    create_annotation(db_session, msg1.id, user.id, project.id, thread_id="X")

    export_data = crud.export_chat_room_data(db_session, room.id)
    assert export_data["export_metadata"]["chat_room_id"] == room.id
    assert export_data["data"]["messages"][0]["turn_id"] == "T1"


def test_one_to_one_accuracy():
    acc = crud._calculate_one_to_one_accuracy(["A", "A", "B"], ["X", "X", "Y"])
    assert acc == 100.0
    acc = crud._calculate_one_to_one_accuracy(["A", "B"], ["X", "Y"])
    assert acc == 100.0
