"""
Test configuration and shared fixtures.

Ensures test isolation from local .env settings (e.g. STORAGE_BACKEND=postgres)
that may be loaded via load_dotenv(override=True) at module import time.
"""

import pytest


@pytest.fixture(autouse=True)
def isolate_env_from_dotenv(monkeypatch, tmp_path):
    """
    Restore safe test defaults for env vars loaded by load_dotenv(override=True).

    dashboard/app.py and pipeline/runner.py call load_dotenv(override=True) at
    import time. When .env has production values (STORAGE_BACKEND=postgres,
    WARM_ONLY_MODE=true), those bleed into all subsequent tests. This fixture
    resets them to the safe local-dev defaults before each test.

    OUTPUTS_DIR is pointed to tmp_path so tests that read from file storage
    always see an empty directory rather than real pipeline output files.
    """
    monkeypatch.setenv("STORAGE_BACKEND", "file")
    monkeypatch.setenv("WARM_ONLY_MODE", "false")
    monkeypatch.setenv("DASHBOARD_AUTH_ENABLED", "false")
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
