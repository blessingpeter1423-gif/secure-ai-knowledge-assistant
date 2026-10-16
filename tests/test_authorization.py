import io
import uuid

from reportlab.pdfgen import canvas
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(
    app,
    base_url="http://127.0.0.1"
)

def create_test_pdf(label: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 750, f"Authorization test: {label}")
    pdf.drawString(72, 730, f"Unique identifier: {uuid.uuid4()}")
    pdf.save()
    return buffer.getvalue()


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


def test_employee_cannot_upload_hr_document():
    token = get_token("alice", "alice123")

    response = client.post(
        "/documents/upload",
        headers={
            "Authorization": f"Bearer {token}"
        },
        files={
            "file": (
                "employee-test.pdf",
                b"%PDF-1.4 employee authorization test",
                "application/pdf"
            )
        },
        data={
            "access_level": "hr"
        }
    )

    assert response.status_code == 403


def test_manager_can_upload_manager_document(monkeypatch):
    monkeypatch.setattr("app.main.process_document", lambda document_id: None)

    token = get_token("bob", "bob123")

    response = client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (
                "manager-test.pdf",
                create_test_pdf("manager"),
                "application/pdf",
            )
        },
        data={"access_level": "manager"},
    )

    assert response.status_code == 200
    assert response.json()["access_level"] == "manager"


def test_hr_can_upload_hr_document(monkeypatch):
    monkeypatch.setattr("app.main.process_document", lambda document_id: None)

    token = get_token("carol", "carol123")

    response = client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": (
                "hr-test.pdf",
                create_test_pdf("hr"),
                "application/pdf",
            )
        },
        data={"access_level": "hr"},
    )

    assert response.status_code == 200
    assert response.json()["access_level"] == "hr"