from conftest import create_user, create_project, create_chat_room, assign_user, auth_headers


def test_projects_assign_remove_errors(client, db_session):
    admin = create_user(db_session, "admin_proj_more", "pass", is_admin=True)
    user = create_user(db_session, "user_proj_more", "pass", is_admin=False)
    project = create_project(db_session, name="proj_more")
    headers = auth_headers(client, "admin_proj_more", "pass")

    # Project not found
    response = client.post(f"/projects/999/assign/{user.id}", headers=headers)
    assert response.status_code == 404

    # User not found
    response = client.post(f"/projects/{project.id}/assign/999", headers=headers)
    assert response.status_code == 404

    # Assign user twice (second is no-op)
    response = client.post(f"/projects/{project.id}/assign/{user.id}", headers=headers)
    assert response.status_code == 204
    response = client.post(f"/projects/{project.id}/assign/{user.id}", headers=headers)
    assert response.status_code == 204

    # Remove assignment
    response = client.delete(f"/projects/{project.id}/assign/{user.id}", headers=headers)
    assert response.status_code == 204

    # Remove non-existent assignment (should still be 204)
    response = client.delete(f"/projects/{project.id}/assign/{user.id}", headers=headers)
    assert response.status_code == 204


def test_get_project_users_project_not_found(client, db_session):
    admin = create_user(db_session, "admin_proj_more2", "pass", is_admin=True)
    headers = auth_headers(client, "admin_proj_more2", "pass")
    response = client.get("/projects/999/users", headers=headers)
    assert response.status_code == 404
