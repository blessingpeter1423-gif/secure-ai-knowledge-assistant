from app.database import SessionLocal
from app.models import Document
from app.retrieval.vector_store import ingest_pdf
from app.audit import create_audit_log


def process_document(document_id: int):
    db = SessionLocal()

    try:
        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        if not document:
            print(
                f"Document {document_id} not found."
            )
            return

        # Prevent unnecessary re-processing.
        if document.status == "indexed":
            print(
                f"Document {document_id} is already indexed."
            )
            return

        document.status = "processing"
        db.commit()

        result = ingest_pdf(
            pdf_path=document.file_path,
            tenant_id=document.tenant.tenant_id,
            access_level=document.access_level,
            document_uuid=document.document_uuid
        )

        document.chunks_stored = result["chunks_stored"]
        document.status = "indexed"

        create_audit_log(
            db=db,
            tenant_id=document.tenant_id,
            user_id=document.uploaded_by,
            action="process_document",
            resource_type="document",
            resource_id=str(document.id),
            status="success"
        )

        db.commit()

        print(
            f"Document {document_id} indexed successfully "
            f"with {document.chunks_stored} chunks."
        )

    except Exception as error:
        db.rollback()

        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        if document:
            document.status = "failed"

            create_audit_log(
                db=db,
                tenant_id=document.tenant_id,
                user_id=document.uploaded_by,
                action="process_document",
                resource_type="document",
                resource_id=str(document.id),
                status="failed"
            )

            db.commit()

        print(
            f"Document {document_id} ingestion failed: {error}"
        )

    finally:
        db.close()