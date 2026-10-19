# Secure AI Knowledge Assistant

![CI](https://github.com/blessingpeter1423-gif/secure-ai-knowledge-assistant/actions/workflows/ci.yml/badge.svg)

A multi-tenant RAG (retrieval-augmented generation) API: employees ask questions about their company's documents, and the system guarantees they only ever see content from **their own company** and **their own access level**. Built with FastAPI, ChromaDB, SQLAlchemy/Alembic, JWT auth and Gemini.

The point of the project is not the chatbot. It is proving, with tests, that one tenant can never read another tenant's data.

## How it works

```
upload PDF --> extract --> chunk --> embed (all-MiniLM-L6-v2) --> ChromaDB
                                                    (metadata: tenant_id, access_level)

question --> JWT auth --> embed question --> vector search
         --> WHERE tenant_id = caller's tenant AND access_level IN caller's allowed levels
         --> relevance threshold --> LLM (context marked untrusted) --> answer + sources
```

(Add an architecture diagram image here.)

## Security design

| Risk | Control |
|---|---|
| Cross-tenant leakage through the vector store | Every query filters on `tenant_id`; tested in both directions |
| Role escalation (employee reading HR content) | `access_level` filter per role: employee, manager, hr, admin; unknown roles are rejected |
| Indirect prompt injection (poisoned documents) | Retrieved text is placed in an `UNTRUSTED CONTEXT` block with explicit rules; a test checks the prompt |
| Credential theft | Passwords hashed with `pwdlib`'s recommended hasher; JWT signing secret required at startup (the app refuses to start without it) |
| Abuse and flooding | Rate limiting with `slowapi` |
| Malicious uploads | Only PDFs accepted; invalid files rejected (tested); upload permissions depend on role |
| Accountability | Audit log and usage-event tables |

## Tests: 30, all passing in CI

- **Authentication and authorization:** login success and failure, protected routes, role-based upload permissions.
- **SQL-side tenant isolation:** Acme users only see Acme documents, Globex users only see Globex documents, and an Acme user cannot fetch a Globex document by ID.
- **Vector-side tenant isolation** (`tests/test_vector_isolation.py`): seeds a temporary collection with documents from both tenants and asserts that an Acme query never retrieves Globex content and vice versa. Positive controls confirm each tenant does retrieve its own content, so the tests cannot pass on empty results.
- **Role isolation:** an employee cannot retrieve HR-level chunks; HR can.
- **Prompt-injection design:** the prompt marks context as untrusted.
- **RAG behaviour:** answers cite sources, and unanswerable questions are refused.

**The isolation tests were verified by sabotage.** I removed the tenant filter from the query and confirmed that exactly the two cross-tenant tests failed with assertion errors, then restored it. A security test that has never failed proves little.

CI runs on every push (GitHub Actions, clean Linux machine, database and sample data built from the seed scripts).

## Testing approach and its limits

- **The LLM is stubbed in tests.** The fake returns the retrieved context, so tests prove retrieval, filtering and source citation, deterministically and without an API key. They do **not** measure answer quality. The live model is checked manually.
- Demo accounts (alice, bob, carol, admin, david) have demo passwords and exist only on sample data. Never reuse them.
- SQLite and a local ChromaDB folder: single-instance, no horizontal scaling.
- Not deployed yet, so there is no live demo link.

## Run locally

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# create .env with JWT_SECRET_KEY and GEMINI_API_KEY
python -m app.init_db
python -m app.seed_database
python -m app.seed_users
python -m app.retrieval.vector_store
uvicorn app.main:app --reload
python -m pytest -q
```

## Related project

The [LLM Security Gateway](https://github.com/blessingpeter1423-gif/llm-security-gateway) is a separate proxy that can sit in front of this app's LLM calls, adding prompt-injection detection, PII filtering and an audit trail.

## What I learned

My 24 tests passed on my machine, but a fresh clone failed straight away, because they quietly depended on a local database, seeded users and a vector store that were never in git. Rebuilding everything from the seed scripts taught me to treat "works on my machine" as unproven. I also learned that a security test needs a positive control: my isolation tests only became trustworthy after I confirmed each tenant can retrieve its own documents, and after I removed the tenant filter and watched the cross-tenant tests fail. I learned that documents can contain malicious instructions intended to manipulate an AI system.
