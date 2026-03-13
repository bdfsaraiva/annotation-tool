import io
import json
import pytest
from starlette.datastructures import UploadFile

from app.api import admin as admin_api
from conftest import create_user, create_project, create_chat_room
from app import crud


@pytest.mark.anyio
async def test_import_chat_room_csv_outer_exception(db_session, monkeypatch, tmp_path):
    admin = create_user(db_session, "admin_err2", "pass", is_admin=True)
    project = create_project(db_session, name="proj_err2")

    # Create a valid CSV file
    csv_content = "turn_id,user_id,turn_text\n1,10,hello\n"
    file_obj = io.BytesIO(csv_content.encode("utf-8"))
    upload = UploadFile(filename="room.csv", file=file_obj)

    # Patch db.commit to raise on second commit (after chat room created)
    commit_calls = {"count": 0}
    original_commit = db_session.commit

    def commit_wrapper():
        commit_calls["count"] += 1
        if commit_calls["count"] >= 2:
            raise Exception("boom")
        return original_commit()

    monkeypatch.setattr(db_session, "commit", commit_wrapper)

    with pytest.raises(Exception):
        await admin_api.create_chat_room_and_import_csv(
            project_id=project.id,
            file=upload,
            db=db_session,
            _=admin
        )


def test_import_batch_annotations_unexpected_error(client, db_session, monkeypatch):
    admin = create_user(db_session, "admin_err3", "pass", is_admin=True)
    project = create_project(db_session, name="proj_err3")
    room = create_chat_room(db_session, project.id, name="room_err3")
    headers = {"Authorization": f"Bearer {client.post('/auth/token', data={'username':'admin_err3','password':'pass'}, headers={'Content-Type':'application/x-www-form-urlencoded'}).json()['access_token']}"}

    # Create a valid JSON file payload
    payload = {
        "batch_metadata": {"project_id": project.id, "chat_room_id": room.id, "import_timestamp": "2026-03-13T00:00:00"},
        "annotators": []
    }

    def boom(*args, **kwargs):
        raise Exception("boom")

    monkeypatch.setattr(admin_api.crud, "import_batch_annotations_for_chat_room", boom)

    response = client.post(
        f"/admin/chat-rooms/{room.id}/import-batch-annotations",
        files={"file": ("batch.json", io.BytesIO(json.dumps(payload).encode("utf-8")), "application/json")},
        headers=headers
    )
    assert response.status_code == 500


def test_admin_update_project_and_delete_chat_room_missing(client, db_session):
    admin = create_user(db_session, "admin_miss", "pass", is_admin=True)
    headers = {"Authorization": f"Bearer {client.post('/auth/token', data={'username':'admin_miss','password':'pass'}, headers={'Content-Type':'application/x-www-form-urlencoded'}).json()['access_token']}"}

    response = client.put("/admin/projects/999", json={"name": "x"}, headers=headers)
    assert response.status_code == 404

    response = client.delete("/admin/chat-rooms/999", headers=headers)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_import_chat_room_csv_message_error(monkeypatch, db_session, tmp_path):
    admin = create_user(db_session, "admin_err4", "pass", is_admin=True)
    project = create_project(db_session, name="proj_err4")

    csv_content = "turn_id,user_id,turn_text\n1,10,hello\n"
    file_obj = io.BytesIO(csv_content.encode("utf-8"))
    upload = UploadFile(filename="room.csv", file=file_obj)

    def boom(*args, **kwargs):
        raise Exception("boom")

    monkeypatch.setattr(crud, "create_chat_message", boom)

    result = await admin_api.create_chat_room_and_import_csv(
        project_id=project.id,
        file=upload,
        db=db_session,
        _=admin
    )
    assert result.import_details.errors
