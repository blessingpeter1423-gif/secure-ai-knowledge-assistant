import chromadb


client = chromadb.PersistentClient(
    path="data/processed/chroma_db"
)

collection = client.get_collection(
    name="company_documents"
)

data = collection.get(
    include=["metadatas", "documents"]
)

print("=" * 80)
print(f"TOTAL CHUNKS: {len(data['ids'])}")
print("=" * 80)

for i, chunk_id in enumerate(data["ids"]):

    print(f"\n{i + 1}. ID:")
    print(chunk_id)

    print("\nMetadata:")
    print(data["metadatas"][i])

    print("\nText:")
    print(data["documents"][i][:150])

    print("-" * 80)