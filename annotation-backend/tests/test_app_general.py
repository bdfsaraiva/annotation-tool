import json

import pytest

from app import crud, models
from app import main as app_main
from app import database as app_database
from app.auth import create_access_token
from conftest import (
    create_user,
    create_project,
    create_chat_room,
    create_message,
    assign_user,
    auth_headers
)


def test_main_root_and_create_first_admin(db_session, client):
    # Ensure tables exist for create_first_admin using database engine.
    models.Base.metadata.create_all(bind=app_database.engine)
    app_main.create_first_admin()

    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "Annotation Tool Backend"


def test_projects_endpoints_more(client, db_session):
    admin = create_user(db_session, "admin_x", "pass", is_admin=True)
    user = create_user(db_session, "user_x", "pass", is_admin=False)
    project = create_project(db_session, name="proj_x")
    room = create_chat_room(db_session, project.id, name="room_x")
    assign_user(db_session, user.id, project.id)

    admin_headers = auth_headers(client, "admin_x", "pass")
    user_headers = auth_headers(client, "user_x", "pass")

    # Admin list projects
    response = client.get("/projects/", headers=admin_headers)
    assert response.status_code == 200

    # Get project as admin
    response = client.get(f"/projects/{project.id}", headers=admin_headers)
    assert response.status_code == 200

    # Get chat room details
    response = client.get(f"/projects/{project.id}/chat-rooms/{room.id}", headers=user_headers)
    assert response.status_code == 200

    # Completion endpoints
    response = client.get(f"/projects/{project.id}/chat-rooms/{room.id}/completion", headers=user_headers)
    assert response.status_code == 200
    response = client.put(
        f"/projects/{project.id}/chat-rooms/{room.id}/completion",
        json={"is_completed": True},
        headers=user_headers
    )
    assert response.status_code == 200

    # Remove assignment
    response = client.delete(f"/projects/{project.id}/assign/{user.id}", headers=admin_headers)
    assert response.status_code == 204


def test_admin_error_branches(client, db_session, tmp_path):
    admin = create_user(db_session, "admin_err", "pass", is_admin=True)
    headers = auth_headers(client, "admin_err", "pass")

    # Create adjacency pairs project without relation types
    response = client.post("/admin/projects", json={"name": "p1", "annotation_type": "adjacency_pairs"}, headers=headers)
    assert response.status_code == 400

    # Get missing project
    response = client.get("/admin/projects/999", headers=headers)
    assert response.status_code == 404

    # Update missing user
    response = client.put("/admin/users/999", json={"username": "valid"}, headers=headers)
    assert response.status_code == 404

    # Import chat room with invalid file
    response = client.post(
        "/admin/projects/999/import-chat-room-csv",
        files={"file": ("bad.txt", b"x", "text/plain")},
        headers=headers
    )
    assert response.status_code in [400, 404]

    # Import batch annotations invalid file type
    response = client.post(
        "/admin/chat-rooms/1/import-batch-annotations",
        files={"file": ("bad.txt", b"x", "text/plain")},
        headers=headers
    )
    assert response.status_code == 400


def test_invalid_token_and_refresh(client, db_session):
    create_user(db_session, "user_tok", "pass", is_admin=False)
    token = create_access_token({"foo": "bar"})
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401

    bad_refresh = create_access_token({"sub": "user_tok"})
    response = client.post("/auth/refresh", json={"refresh_token": bad_refresh})
    assert response.status_code == 401
