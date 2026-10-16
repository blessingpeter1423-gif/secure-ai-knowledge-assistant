from app.retrieval.search import search_documents


def get_documents(results):
    return results["documents"][0]


def test_tenant_isolation():

    results = search_documents(
        "Globex confidential information",
        tenant_id="acme",
        user_role="employee",
        number_of_results=3
    )

    documents = get_documents(results)

    for document in documents:
        assert "globex" not in document.lower()


def test_employee_cannot_access_hr_documents():

    results = search_documents(
        "HR employee information",
        tenant_id="acme",
        user_role="employee",
        number_of_results=3
    )

    documents = get_documents(results)

    for document in documents:
        assert "hr" not in document.lower()


def test_invalid_role_is_rejected():

    try:

        search_documents(
            "company information",
            tenant_id="acme",
            user_role="superuser",
            number_of_results=3
        )

        assert False, "Invalid role should have been rejected."

    except ValueError:
        pass