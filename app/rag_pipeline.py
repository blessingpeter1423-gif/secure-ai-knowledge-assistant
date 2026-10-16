from app.auth.users import get_user
from app.retrieval.search import (
    search_documents,
    filter_relevant_results
)
from app.generation.llm import generate_answer


def build_context(results):
    """
    Build context for the LLM while preserving
    document source and page information.
    """

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    context_parts = []

    for i, (document, metadata) in enumerate(
        zip(documents, metadatas),
        start=1
    ):

        source = metadata.get(
            "source",
            "Unknown source"
        )

        page = metadata.get(
            "page",
            "Unknown page"
        )

        context_parts.append(
            f"""
SOURCE {i}
Document: {source}
Page: {page}

Content:
{document}
"""
        )

    return "\n".join(context_parts)


def answer_question(
    question: str,
    tenant_id: str,
    user_role: str
):

    # 1. Search the knowledge base
    results = search_documents(
    question,
    tenant_id=tenant_id,
    user_role=user_role,
    number_of_results=3
)
    # 2. Remove weakly relevant results
    results = filter_relevant_results(
        results
    )

    # 3. Refuse if nothing relevant was found
    if not results["documents"][0]:

        return (
            "I don't have enough information "
            "in the provided documents.",
            []
        )

    # 4. Build context
    context = build_context(results)

    # 5. Generate answer
    answer = generate_answer(
        question,
        context
    )

    # ...

    # 4. Extract sources
    metadatas = results["metadatas"][0]

    sources = []

    for metadata in metadatas:

        source = metadata.get(
            "source",
            "Unknown source"
        )

        page = metadata.get(
            "page",
            "Unknown page"
        )

        citation = f"{source} — Page {page}"

        if citation not in sources:
            sources.append(citation)

    return answer, sources


def main():

    print("=" * 60)
    print("SECURE AI KNOWLEDGE ASSISTANT")
    print("=" * 60)

    print("\nAsk a question about the company documents.")
    print("Type 'exit' to quit.")

    username = input("\nUsername: ")

    user = get_user(username)

    if not user:
        print("\nAuthentication failed.")
        return

    tenant_id = user["tenant_id"]
    user_role = user["role"]

    print("\nLogin successful.")
    print(f"User: {username}")
    print(f"Role: {user_role}")
    print(f"Tenant: {tenant_id}")

    while True:

        question = input("\nYou: ").strip()

        if question.lower() == "exit":

            print("\nGoodbye!")
            break

        if not question:

            print("Please enter a question.")
            continue

        try:

            answer, sources = answer_question(
                question,
                tenant_id,
                user_role
            )

            print("\nAssistant:")
            print("-" * 60)
            print(answer)

            print("\nSources:")
            for source in sources:
                print(f"- {source}")

        except Exception as error:

            print("\nERROR")
            print("-" * 60)
            print(type(error).__name__)
            print(error)


if __name__ == "__main__":
    main()