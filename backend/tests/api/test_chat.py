# File: backend/tests/api/test_chat.py
# Purpose: Validate chat and attachment endpoints with SSE responses.
import json


def test_chat_stream_basic(app_client):
    init_response = app_client.post("/api/session/init", json={})
    data = init_response.json()
    payload = {
        "message": "测试消息",
        "model": "gpt-4o-mini",
        "user_id": data["user_id"],
        "session_id": data["active_session_id"],
    }
    with app_client.stream("POST", "/api/chat", json=payload, timeout=5) as response:
        assert response.status_code == 200
        content = ""
        for chunk in response.iter_text():
            content += chunk
            if "event: content" in content and "data:" in content:
                break
        assert "event: content" in content
        response.close()
        data_line = next(
            (line for line in content.splitlines() if line.startswith("data: ")),
            "",
        )
        data_json = data_line.replace("data: ", "", 1)
        assert json.loads(data_json) == "测试响应"


def test_chat_invalid_model(app_client):
    init_response = app_client.post("/api/session/init", json={})
    data = init_response.json()
    payload = {
        "message": "测试消息",
        "model": "invalid-model",
        "user_id": data["user_id"],
        "session_id": data["active_session_id"],
    }
    with app_client.stream("POST", "/api/chat", json=payload, timeout=5) as response:
        assert response.status_code == 200
        content = ""
        for chunk in response.iter_text():
            content += chunk
            if "data:" in content:
                break
        response.close()
        data_line = next(
            (line for line in content.splitlines() if line.startswith("data: ")),
            "",
        )
        data_json = data_line.replace("data: ", "", 1)
        assert json.loads(data_json) == "Unsupported model"


def test_upload_and_chat_with_attachment(app_client):
    init_response = app_client.post("/api/session/init", json={})
    data = init_response.json()

    file_response = app_client.post(
        "/api/files",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert file_response.status_code == 200
    upload = file_response.json()
    assert upload["id"]

    payload = {
        "message": "请总结附件",
        "model": "gpt-4o-mini",
        "user_id": data["user_id"],
        "session_id": data["active_session_id"],
        "attachments": [
            {
                "file_id": upload["id"],
                "filename": upload["filename"],
                "content_type": upload["content_type"],
            }
        ],
    }
    with app_client.stream("POST", "/api/chat", json=payload, timeout=5) as response:
        assert response.status_code == 200
        content = ""
        for chunk in response.iter_text():
            content += chunk
            if "event: content" in content and "data:" in content:
                break
        assert "event: content" in content
        response.close()
