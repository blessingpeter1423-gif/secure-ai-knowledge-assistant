from types import SimpleNamespace

import pytest

from app.generation import llm
from app.main import app


@pytest.fixture(autouse=True)
def disable_rate_limits_during_tests():
    limiter = app.state.limiter
    original_enabled = limiter.enabled
    limiter.enabled = False

    yield

    limiter.enabled = original_enabled


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    """Replace the Gemini call with a stand-in that returns the retrieved context.

    Tests then prove retrieval, tenant filtering and source citation without
    a network call or a real API key.
    """

    def fake_generate_content(*, model, contents):
        context = contents.split("UNTRUSTED CONTEXT")[1].split("USER QUESTION")[0]
        return SimpleNamespace(text=context)

    monkeypatch.setattr(llm.client.models, "generate_content", fake_generate_content)