from pathlib import Path
import hashlib

import chromadb
from sentence_transformers import SentenceTransformer

from app.ingestion.pdf_loader import load_pdf
from app.ingestion.text_splitter import process_pages


embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(
    path="data/processed/chroma_db"
)

collection = client.get_or_create_collection(
    name="company_documents"
)


def ingest_pdf(
    pdf_path: str,
    tenant_id: str,
    access_level: str = "employee"
):
    """
    Extract, chunk, embed, and store a PDF in ChromaDB.

    The document is associated with the authenticated
    user's tenant and access level.
    """

    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {pdf_path}"
        )

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            "Only PDF files are supported."
        )

    pages = load_pdf(
        str(path)
    )

    processed_chunks = process_pages(
        pages
    )

    if not processed_chunks:
        raise ValueError(
            "No text could be extracted from the PDF."
        )

    documents = []
    ids = []
    metadatas = []

    document_hash = hashlib.sha256(
        str(path.resolve()).encode()
    ).hexdigest()[:16]

    for item in processed_chunks:

        documents.append(
            item["chunk"]
        )

        page = item["page"]
        chunk_number = item["chunk_number"]

        ids.append(
            f"{tenant_id}_{document_hash}_"
            f"page_{page}_chunk_{chunk_number}"
        )

        metadatas.append(
            {
                "source": path.name,
                "page": page,
                "chunk_number": chunk_number,
                "tenant_id": tenant_id,
                "access_level": access_level
            }
        )

    embeddings = embedding_model.encode(
        documents
    ).tolist()

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
        f"Chunks stored: {result['chunks_stored']}"
    )