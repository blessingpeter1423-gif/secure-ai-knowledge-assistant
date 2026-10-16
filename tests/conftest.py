import pytest

from app.main import app


@pytest.fixture(autouse=True)
def disable_rate_limits_during_tests():
    limiter = app.state.limiter
    original_enabled = limiter.enabled
    limiter.enabled = False

    yield

    limiter.enabled = original_enabled
