import uuid
from pathlib import Path
import hashlib

import chromadb
from sentence_transformers import SentenceTransformer

from app.ingestion.pdf_loader import load_pdf
from app.ingestion.text_splitter import process_pages


# ---------------------------------------------------------
# Embedding model
# ---------------------------------------------------------

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


# ---------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------

client = chromadb.PersistentClient(
    path="data/processed/chroma_db"
)

collection = client.get_or_create_collection(
    name="company_documents"
)


# ---------------------------------------------------------
# PDF ingestion
# ---------------------------------------------------------

def ingest_pdf(
    pdf_path: str,
    tenant_id: str,
    access_level: str = "employee",
    document_uuid: str | None = None
):
    """
    Extract, chunk, embed, and store a PDF in ChromaDB.

    Every stored chunk receives:
        - source
        - page
        - chunk number
        - tenant ID
        - access level
    """

    path = Path(pdf_path)

    # Validate file
    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {pdf_path}"
        )

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            "Only PDF files are supported."
        )

    if not tenant_id:
        raise ValueError(
            "tenant_id is required."
        )

    # -----------------------------------------------------
    # Extract PDF text
    # -----------------------------------------------------

    pages = load_pdf(
        str(path)
    )

    if not pages:
        raise ValueError(
            "No readable text was found in the PDF."
        )

    # -----------------------------------------------------
    # Clean and split into chunks
    # -----------------------------------------------------

    processed_chunks = process_pages(
        pages
    )

    if not processed_chunks:
        raise ValueError(
            "No text chunks were created from the PDF."
        )

    # -----------------------------------------------------
    # Prepare ChromaDB data
    # -----------------------------------------------------

    documents = []
    ids = []
    metadatas = []

    # Create a stable identifier for this file
    file_identifier = hashlib.sha256(
        str(path.resolve()).encode()
    ).hexdigest()[:16]

    for item in processed_chunks:

        chunk = item["chunk"]
        page = item["page"]
        chunk_number = item["chunk_number"]

        documents.append(
            chunk
        )

        ids.append(
            f"{document_uuid or file_identifier}_"
            f"page_{page}_chunk_{chunk_number}"
        )

        metadatas.append(
            {
                "source": path.name,
                "page": page,
                "chunk_number": chunk_number,
                "tenant_id": tenant_id,
                "access_level": access_level,
                "document_uuid": document_uuid or ""
            }
        )

    # -----------------------------------------------------
    # Generate embeddings
    # -----------------------------------------------------

    embeddings = embedding_model.encode(
        documents
    ).tolist()

    # -----------------------------------------------------
    # Store in ChromaDB
    # -----------------------------------------------------

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return {
        "filename": path.name,
        "tenant_id": tenant_id,
        "access_level": access_level,
        "chunks_stored": len(documents)
    }


# ---------------------------------------------------------
# Manual test
# ---------------------------------------------------------

if __name__ == "__main__":

    result = ingest_pdf(
        "data/raw/employee_handbook.pdf",
        tenant_id="acme",
        access_level="employee"
    )

    print(
        "Document successfully stored."
    )

    print(
        f"File: {result['filename']}"
    )

    print(
        f"Tenant: {result['tenant_id']}"
    )

    print(
        f"Access level: {result['access_level']}"
    )

    print(
        f"Chunks stored: {result['chunks_stored']}"
    )