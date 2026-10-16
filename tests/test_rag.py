from app.rag_pipeline import answer_question


def test_annual_leave_policy():
    answer, sources = answer_question(
        "How many annual leave days do full-time employees receive?",
        tenant_id="acme",
        user_role="employee"
    )

    assert "20" in answer
    assert sources


def test_leave_request_notice():
    answer, sources = answer_question(
        "How many days before leave should an employee submit a request?",
        tenant_id="acme",
        user_role="employee"
    )

    assert "7" in answer
    assert sources


def test_lost_laptop_policy():
    answer, sources = answer_question(
        "What should an employee do if their company laptop is lost or stolen?",
        tenant_id="acme",
        user_role="employee"
    )

    assert "24 hours" in answer
    assert sources


def test_remote_work_policy():
    answer, sources = answer_question(
        "How many days per week can employees work remotely?",
        tenant_id="acme",
        user_role="employee"
    )

    assert "two" in answer.lower() or "2" in answer
    assert sources


def test_unknown_question_is_refused():
    answer, sources = answer_question(
        "What is the company policy for employee bonuses?",
        tenant_id="acme",
        user_role="employee"
    )

    assert answer == "I don't have enough information in the provided documents."
    assert sources == []


def test_answers_include_sources():
    questions = [
        "How many annual leave days do full-time employees receive?",
        "How many days before leave should an employee submit a request?",
        "What should an employee do if their company laptop is lost or stolen?",
        "How many days per week can employees work remotely?"
    ]

    for question in questions:
        answer, sources = answer_question(
            question,
            tenant_id="acme",
            user_role="employee"
        )

        assert answer
        assert sources