from fastapi.testclient import TestClient

from app.main import app


client = TestClient(
    app,
    base_url="http://127.0.0.1"
)


def get_token(username: str, password: str):
    response = client.post(
        "/login",
        data={
            "username": username,
            "password": password
        }
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def test_login_success():
    response = client.post(
        "/login",
        data={
            "username": "alice",
            "password": "alice123"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password():
    response = client.post(
        "/login",
        data={
            "username": "alice",
            "password": "wrong-password"
        }
    )

    assert response.status_code == 401


def test_ask_requires_authentication():
    response = client.post(
        "/ask",
        json={
            "question": "How many annual leave days do employees receive?"
        }
    )

    assert response.status_code == 401


def test_ask_authenticated_user(monkeypatch):
    from app.main import app

    monkeypatch.setattr(
        "app.main.answer_question",
        lambda *args, **kwargs: (
            "Full-time employees receive 20 days of annual leave each year.",
            ["employee_handbook.pdf — Page 1"],
        ),
    )

    token = get_token("alice", "alice123")

    response = client.post(
        "/ask",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question": "How many annual leave days do full-time employees receive?"
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert "20" in data["answer"]
    assert len(data["sources"]) > 0

def test_documents_requires_authentication():
    response = client.get("/documents")

    assert response.status_code == 401


def test_documents_authenticated_user():
    token = get_token(
        "alice",
        "alice123"
    )

    response = client.get(
        "/documents",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200

    documents = response.json()

    assert isinstance(documents, list)


def test_empty_question_is_rejected():
    token = get_token(
        "alice",
        "alice123"
    )

    response = client.post(
        "/ask",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "question": "   "
        }
    )

    assert response.status_code == 400


def test_invalid_pdf_upload_is_rejected():
    token = get_token(
        "alice",
        "alice123"
    )

    response = client.post(
        "/documents/upload",
        headers={
            "Authorization": f"Bearer {token}"
        },
        files={
            "file": (
                "malicious.txt",
                b"This is not a PDF.",
                "text/plain"
            )
        },
        data={
            "access_level": "employee"
        }
    )

    assert response.status_code == 400