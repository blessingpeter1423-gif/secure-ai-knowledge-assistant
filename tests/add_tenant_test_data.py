import chromadb
from sentence_transformers import SentenceTransformer


embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

client = chromadb.PersistentClient(
    path="data/processed/chroma_db"
)

collection = client.get_collection(
    name="company_documents"
)


documents = [
    {
        "id": "tenant_test_globex",
        "text": (
            "Globex Corporation's secret project code name "
            "is Project Phoenix. This information belongs "
            "exclusively to Globex Corporation."
        ),
        "tenant_id": "globex"
    },
    {
        "id": "tenant_test_acme",
        "text": (
            "Acme Technology's secret project code name "
            "is Project Atlas. This information belongs "
            "exclusively to Acme Technology."
        ),
        "tenant_id": "acme"
    }
]


for item in documents:

    embedding = embedding_model.encode(
        item["text"]
    ).tolist()

    collection.upsert(
        ids=[item["id"]],
        documents=[item["text"]],
        embeddings=[embedding],
        metadatas=[
            {
                "source": "tenant_isolation_test.txt",
                "page": 1,
                "chunk_number": 1,
                "tenant_id": item["tenant_id"],
                "access_level": "employee"
            }
        ]
    )

    print(
        f"Added test document for "
        f"{item['tenant_id']}"
    )


print("\nTenant isolation test data added.")