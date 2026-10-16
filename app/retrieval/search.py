import chromadb
from sentence_transformers import SentenceTransformer


# --------------------------------------------------
# 1. Load embedding model
# --------------------------------------------------

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


# --------------------------------------------------
# 2. Connect to ChromaDB
# --------------------------------------------------

client = chromadb.PersistentClient(
    path="data/processed/chroma_db"
)


# --------------------------------------------------
# 3. Get document collection
# --------------------------------------------------

collection = client.get_or_create_collection(
    name="company_documents"
)


# --------------------------------------------------
# 4. Search documents
# --------------------------------------------------

def search_documents(
    question: str,
    tenant_id: str,
    user_role: str,
    number_of_results: int = 3
):
    """
    Search documents while enforcing tenant and role access.
    """

    question_embedding = embedding_model.encode(
        question
    ).tolist()

    allowed_access_levels = {
        "employee": ["employee"],
        "manager": ["employee", "manager"],
        "hr": ["employee", "manager", "hr"],
        "admin": ["employee", "manager", "hr", "admin"]
    }

    if user_role not in allowed_access_levels:
        raise ValueError(
            f"Unknown user role: {user_role}"
        )

    allowed_levels = allowed_access_levels[user_role]

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=number_of_results,
        where={
            "$and": [
                {
                    "tenant_id": tenant_id
                },
                {
                    "access_level": {
                        "$in": allowed_levels
                    }
                }
            ]
        }
    )

    return results

# --------------------------------------------------
# 5. Filter by relevance
# --------------------------------------------------

def filter_relevant_results(
    results,
    max_distance: float = 1.25
):
    """
    Keep only results whose distance is below
    the configured relevance threshold.

    Lower distance = more similar.
    """

    documents = results["documents"][0]
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]

    filtered_documents = []
    filtered_distances = []
    filtered_metadatas = []

    for document, distance, metadata in zip(
        documents,
        distances,
        metadatas
    ):

        if distance <= max_distance:

            filtered_documents.append(
                document
            )

            filtered_distances.append(
                distance
            )

            filtered_metadatas.append(
                metadata
            )

    return {
        "documents": [filtered_documents],
        "distances": [filtered_distances],
        "metadatas": [filtered_metadatas]
    }


# --------------------------------------------------
# 6. Test search
# --------------------------------------------------

if __name__ == "__main__":

    question = input(
        "\nAsk a question: "
    )

    results = search_documents(
        question=question,
        tenant_id="acme",
        user_role="employee",
        number_of_results=3
    )

    results = filter_relevant_results(
        results
    )

    print("\nRELEVANT INFORMATION")
    print("-" * 60)

    documents = results["documents"][0]
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]

    if not documents:

        print(
            "No sufficiently relevant information "
            "was found."
        )

    else:

        for i, (
            document,
            distance,
            metadata
        ) in enumerate(
            zip(
                documents,
                distances,
                metadatas
            ),
            start=1
        ):

            print(f"\nResult {i}")

            print(
                f"Source: {metadata['source']} "
                f"(Page {metadata['page']})"
            )

            print(
                f"Distance: {distance:.4f}"
            )

            print(
                f"Content: {document}"
            )