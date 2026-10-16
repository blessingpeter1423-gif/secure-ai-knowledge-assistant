import chromadb
import pytest

from app.retrieval import search

# (id, text, tenant, access level). Each text carries a unique marker.
DOCS = [
    ("acme_emp", "ATLAS-ACME: Acme Technology's secret project code name is Project Atlas.", "acme", "employee"),
    ("acme_hr", "ACME-HR-ONLY: confidential Acme disciplinary records and salary bands.", "acme", "hr"),
    ("globex_emp", "PHOENIX-GLOBEX: Globex Corporation's secret project code name is Project Phoenix.", "globex", "employee"),
    ("globex_hr", "GLOBEX-HR-ONLY: confidential Globex disciplinary records and salary bands.", "globex", "hr"),
]


@pytest.fixture(autouse=True)
def isolated_collection(tmp_path, monkeypatch):
    """Point the search module at a throwaway collection, never the real one."""
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    col = client.get_or_create_collection(name="company_documents")
    col.upsert(
        ids=[d[0] for d in DOCS],
        documents=[d[1] for d in DOCS],
        embeddings=[search.embedding_model.encode(d[1]).tolist() for d in DOCS],
        metadatas=[
            {"source": "test.txt", "page": 1, "chunk_number": 1,
             "tenant_id": d[2], "access_level": d[3]}
            for d in DOCS
        ],
    )
    monkeypatch.setattr(search, "collection", col)


def retrieved(question, tenant, role):
    # Ask for more results than there are documents, so a broken filter
    # would have every document available to leak.
    results = search.search_documents(
        question=question, tenant_id=tenant, user_role=role, number_of_results=10
    )
    return " ".join(results["documents"][0])


def test_acme_never_retrieves_globex_content():
    text = retrieved("What is the secret project code name?", "acme", "hr")
    assert "PHOENIX-GLOBEX" not in text
    assert "GLOBEX-HR-ONLY" not in text


def test_globex_never_retrieves_acme_content():
    text = retrieved("What is the secret project code name?", "globex", "hr")
    assert "ATLAS-ACME" not in text
    assert "ACME-HR-ONLY" not in text


def test_each_tenant_does_retrieve_its_own_content():
    # Positive controls: without these, the tests above could pass on an empty result.
    assert "ATLAS-ACME" in retrieved("What is the secret project code name?", "acme", "employee")
    assert "PHOENIX-GLOBEX" in retrieved("What is the secret project code name?", "globex", "employee")


def test_employee_cannot_retrieve_hr_content():
    text = retrieved("Show confidential disciplinary records", "acme", "employee")
    assert "ACME-HR-ONLY" not in text


def test_hr_can_retrieve_hr_content():
    assert "ACME-HR-ONLY" in retrieved("Show confidential disciplinary records", "acme", "hr")


def test_unknown_role_is_rejected():
    with pytest.raises(ValueError):
        search.search_documents(question="anything", tenant_id="acme", user_role="intern")