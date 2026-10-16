import hashlib
import uuid

from app.database import SessionLocal
from app.models import Document, User
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


def test_acme_user_only_sees_acme_documents():
    token = get_token("alice", "alice123")

    response = client.get(
        "/documents",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200

    documents = response.json()

    for document in documents:
        detail_response = client.get(
            f"/documents/{document['document_id']}",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )

        assert detail_response.status_code == 200


def test_globex_user_only_sees_globex_documents():
    token = get_token("david", "david123")

    response = client.get(
        "/documents",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200

    documents = response.json()

    for document in documents:
        detail_response = client.get(
            f"/documents/{document['document_id']}",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )

        assert detail_response.status_code == 200


def test_acme_user_cannot_access_globex_document():
    db = SessionLocal()
    document = None

    try:
        globex_user = (
            db.query(User)
            .filter(User.username == "david")
            .first()
        )
        assert globex_user is not None

        unique_value = str(uuid.uuid4())

        document = Document(
            document_uuid=unique_value,
            content_hash=hashlib.sha256(
                unique_value.encode()
            ).hexdigest(),
            filename="globex-private-test.pdf",
            file_path=f"data/raw/globex/{unique_value}.pdf",
            tenant_id=globex_user.tenant_id,
            uploaded_by=globex_user.id,
            access_level="employee",
            chunks_stored=0,
            status="failed",
        )

        db.add(document)
        db.commit()
        db.refresh(document)
        document_id = document.id

    finally:
        db.close()

    try:
        acme_token = get_token("alice", "alice123")

        response = client.get(
            f"/documents/{document_id}",
            headers={
                "Authorization": f"Bearer {acme_token}"
            },
        )

        assert response.status_code == 404

    finally:
        cleanup_db = SessionLocal()
        try:
            test_document = (
                cleanup_db.query(Document)
                .filter(Document.id == document_id)
                .first()
            )
            if test_document:
                cleanup_db.delete(test_document)
                cleanup_db.commit()
        finally:
            cleanup_db.close()