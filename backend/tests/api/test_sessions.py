# File: backend/tests/api/test_sessions.py
# Purpose: Cover session lifecycle and user paths APIs.
from pathlib import Path


def test_session_init_and_create(app_client):
    init_response = app_client.post("/api/session/init", json={})
    assert init_response.status_code == 200
    init_data = init_response.json()
    assert init_data["user_id"]
    assert init_data["active_session_id"]

    create_response = app_client.post(
        "/api/session/new",
        json={"user_id": init_data["user_id"], "title": "测试会话"},
    )
    assert create_response.status_code == 200
    session = create_response.json()
    assert session["id"]
    assert session["title"] == "测试会话"

    get_response = app_client.get(
        f"/api/session/{session['id']}?user_id={init_data['user_id']}"
    )
    assert get_response.status_code == 200
    loaded = get_response.json()
    assert loaded["id"] == session["id"]


def test_user_paths_flow(app_client, tmp_path):
    init_response = app_client.post("/api/session/init", json={})
    user_id = init_response.json()["user_id"]

    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir(parents=True, exist_ok=True)
    set_response = app_client.post(
        "/api/user/paths",
        json={"user_id": user_id, "paths": [str(allowed_dir)]},
    )
    assert set_response.status_code == 200
    set_data = set_response.json()
    assert str(allowed_dir) in set_data["paths"]

    get_response = app_client.get(f"/api/user/paths?user_id={user_id}")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert str(allowed_dir) in get_data["paths"]
