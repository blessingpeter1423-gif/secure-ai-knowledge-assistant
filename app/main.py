import hashlib
import uuid
from pathlib import Path

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    UploadFile,
    File,
    Form,
    Request,
    BackgroundTasks
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models import Document, AuditLog, UsageEvent
from app.audit import (
    create_audit_log,
    record_usage
)
from app.security_headers import SecurityHeadersMiddleware
from app.auth.users import get_user
from app.auth.security import (
    verify_password,
    create_access_token,
    get_current_user
)
from app.database import get_db
from app.rag_pipeline import answer_question
from app.ingestion.background import process_document
limiter = Limiter(
    key_func=get_remote_address
)


app = FastAPI(
    title="Secure AI Knowledge Assistant",
    description="Secure enterprise RAG API",
    version="1.0.0"
)
app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "127.0.0.1",
        "localhost"
    ]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"]
)
app.add_middleware(
    SecurityHeadersMiddleware
)



class TokenResponse(BaseModel):

    access_token: str
    token_type: str


class QuestionRequest(BaseModel):

    question: str


class QuestionResponse(BaseModel):

    answer: str
    sources: list[str]


@app.get("/")
def health_check():

    return {
        "status": "ok",
        "message": "Secure AI Knowledge Assistant API is running."
    }


@app.post(
    "/login",
    response_model=TokenResponse
)
@limiter.limit("10/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    user = get_user(
        db,
        form_data.username
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password."
        )

    if not verify_password(
        form_data.password,
        user.password_hash
    ):

        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password."
        )

    access_token = create_access_token(
        user.username
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@app.post(
    "/ask",
    response_model=QuestionResponse
)
@limiter.limit("20/minute")
def ask_question(
    request: Request,
    request_data: QuestionRequest,
    current_user=Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    question = request_data.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    try:

        answer, sources = answer_question(
            question,
            tenant_id=current_user.tenant.tenant_id,
            user_role=current_user.role.name
        )

        create_audit_log(
            db=db,
            tenant_id=current_user.tenant.id,
            user_id=current_user.id,
            action="ask_question",
            resource_type="rag_query",
            status="success"
        )

        record_usage(
            db=db,
            tenant_id=current_user.tenant.id,
            user_id=current_user.id,
            event_type="question",
            quantity=1
        )

        db.commit()

        return QuestionResponse(
            answer=answer,
            sources=sources
        )

    except Exception as error:

        db.rollback()

        create_audit_log(
            db=db,
            tenant_id=current_user.tenant.id,
            user_id=current_user.id,
            action="ask_question",
            resource_type="rag_query",
            status="failed"
        )

        db.commit()

        print(
            f"Internal error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="An internal error occurred."
        ) from error
@app.post("/documents/upload")
@limiter.limit("5/minute")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    access_level: str = Form("employee"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    allowed_levels = {
        "employee": ["employee"],
        "manager": ["employee", "manager"],
        "hr": ["employee", "manager", "hr"],
        "admin": ["employee", "manager", "hr", "admin"]
    }

    user_role = current_user.role.name

    if user_role not in allowed_levels:
        raise HTTPException(
            status_code=403,
            detail="User role is not permitted."
        )

    if access_level not in allowed_levels[user_role]:
        raise HTTPException(
            status_code=403,
            detail=(
                f"You cannot create a document with "
                f"access level '{access_level}'."
            )
        )

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required."
        )

    filename = Path(file.filename).name

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="File must have a .pdf extension."
        )

    contents = await file.read()

    max_size = 10 * 1024 * 1024

    if len(contents) > max_size:
        raise HTTPException(
            status_code=400,
            detail="File is too large. Maximum size is 10 MB."
        )

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    # Verify that the file actually looks like a PDF.
    if not contents.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid PDF."
        )

    content_hash = hashlib.sha256(contents).hexdigest()

    # Prevent the same document from being uploaded twice
    # within the same tenant.
    existing_document = (
        db.query(Document)
        .filter(
            Document.tenant_id == current_user.tenant.id,
            Document.content_hash == content_hash
        )
        .first()
    )

    if existing_document:
        raise HTTPException(
            status_code=409,
            detail="This document has already been uploaded."
        )

    tenant_id = current_user.tenant.tenant_id

    upload_directory = Path(
        f"data/raw/{tenant_id}"
    )

    upload_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    # Generate a unique storage filename.
    document_uuid = str(uuid.uuid4())
    stored_filename = f"{document_uuid}.pdf"
    file_path = upload_directory / stored_filename

    try:
        # Save the physical PDF.
        with open(file_path, "wb") as output_file:
            output_file.write(contents)

        # Create the database record.
        document = Document(
            document_uuid=document_uuid,
            filename=filename,
            file_path=str(file_path),
            tenant_id=current_user.tenant.id,
            uploaded_by=current_user.id,
            access_level=access_level,
            content_hash=content_hash,
            chunks_stored=0,
            status="processing"
        )

        db.add(document)

        # Generate the database ID without committing yet.
        db.flush()

        # Record the upload in the audit log.
        create_audit_log(
            db=db,
            tenant_id=current_user.tenant.id,
            user_id=current_user.id,
            action="upload_document",
            resource_type="document",
            resource_id=str(document.id),
            status="success"
        )

        # Record usage.
        record_usage(
            db=db,
            tenant_id=current_user.tenant.id,
            user_id=current_user.id,
            event_type="document_upload",
            quantity=1
        )

        # Commit the document + audit + usage together.
        db.commit()

        # Start document processing after the database transaction
        # has successfully completed.
        background_tasks.add_task(
            process_document,
            document.id
        )

        return {
            "message": (
                "Document uploaded successfully "
                "and is being processed."
            ),
            "document_id": document.id,
            "document_uuid": document.document_uuid,
            "filename": document.filename,
            "tenant_id": tenant_id,
            "access_level": document.access_level,
            "chunks_stored": 0,
            "status": "processing"
        }

    except Exception as error:
        db.rollback()

        # Remove the physical file if database processing failed.
        if file_path.exists():
            file_path.unlink()

        print(
            f"Document upload error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Document could not be uploaded."
        ) from error
@app.get("/documents")
def list_documents(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    documents = (
        db.query(Document)
        .filter(
            Document.tenant_id == current_user.tenant.id
        )
        .order_by(
            Document.created_at.desc()
        )
        .all()
    )

    return [
        {
            "document_id": document.id,
            "filename": document.filename,
            "access_level": document.access_level,
            "chunks_stored": document.chunks_stored,
            "status": document.status,
            "uploaded_by": document.uploaded_by_user.username,
            "created_at": document.created_at
        }
        for document in documents
    ]
@app.get("/documents/{document_id}")
def get_document(
    document_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.tenant_id == current_user.tenant.id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    return {
        "document_id": document.id,
        "document_uuid": document.document_uuid,
        "filename": document.filename,
        "access_level": document.access_level,
        "chunks_stored": document.chunks_stored,
        "status": document.status,
        "uploaded_by": document.uploaded_by_user.username,
        "created_at": document.created_at
    }
@app.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.name not in ["manager", "hr", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete documents."
        )

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.tenant_id == current_user.tenant.id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    document_uuid = document.document_uuid
    filename = document.filename
    file_path = Path(document.file_path)

    try:
        from app.retrieval.vector_store import collection

        # Remove this document's chunks from Chroma.
        collection.delete(
            where={
                "document_uuid": document_uuid
            }
        )

        # Check whether another database record still
        # references the same physical file.
        other_document = (
            db.query(Document)
            .filter(
                Document.file_path == document.file_path,
                Document.id != document.id
            )
            .first()
        )

        # Only remove the physical file when no other
        # document record is using it.
        if (
            other_document is None
            and file_path.exists()
        ):
            file_path.unlink()

        create_audit_log(
            db=db,
            tenant_id=current_user.tenant.id,
            user_id=current_user.id,
            action="delete_document",
            resource_type="document",
            resource_id=str(document.id),
            status="success"
        )

        record_usage(
            db=db,
            tenant_id=current_user.tenant.id,
            user_id=current_user.id,
            event_type="document_delete",
            quantity=1
        )

        db.delete(document)
        db.commit()

    except Exception as error:
        db.rollback()

        print(
            f"Document deletion error: {error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Document could not be deleted."
        ) from error

    return {
        "message": "Document deleted successfully.",
        "document_id": document_id,
        "document_uuid": document_uuid,
        "filename": filename
    }
@app.get("/audit-logs")
def get_audit_logs(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if current_user.role.name not in [
        "hr",
        "admin"
    ]:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view audit logs."
        )

    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.tenant_id == current_user.tenant.id
        )
        .order_by(
            AuditLog.created_at.desc()
        )
        .limit(100)
        .all()
    )

    return [
        {
            "id": log.id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "status": log.status,
            "user": (
                log.user.username
                if log.user
                else None
            ),
            "created_at": log.created_at
        }
        for log in logs
    ]
@app.get("/usage")
def get_usage(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if current_user.role.name not in [
        "manager",
        "hr",
        "admin"
    ]:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view usage."
        )

    events = (
        db.query(UsageEvent)
        .filter(
            UsageEvent.tenant_id == current_user.tenant.id
        )
        .all()
    )

    usage = {}

    for event in events:

        usage[event.event_type] = (
            usage.get(event.event_type, 0)
            + event.quantity
        )

    return {
        "tenant_id": current_user.tenant.tenant_id,
        "usage": usage
    }