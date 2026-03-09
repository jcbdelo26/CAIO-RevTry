"""Tests for persistence backend selection and warm storage contracts."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from models.schemas import (
    ConversationSentiment,
    ConversationStage,
    DraftApprovalStatus,
    FollowUpDraft,
    FollowUpTrigger,
    UrgencyLevel,
)
from persistence.factory import get_storage_backend
from persistence.file_store import FileStorageBackend
from persistence.postgres_store import PostgresStorageBackend


def _build_followup(draft_id: str, business_date: str) -> FollowUpDraft:
    return FollowUpDraft(
        draftId=draft_id,
        contactId=f"contact-{draft_id}",
        ghlContactId=f"ghl-{draft_id}",
        sourceConversationId="conv-1",
        businessDate=business_date,
        generationRunId=f"run-{draft_id}",
        contactEmail="alex@acme.com",
        contactName="Alex Morgan",
        companyName="Acme",
        subject="Timing options for next week",
        body="Alex,\n\nThanks for the note.\n\nDani Apgar\nHead of Sales, Chief AI Officer",
        trigger=FollowUpTrigger.AWAITING_OUR_RESPONSE,
        urgency=UrgencyLevel.HOT,
        sentiment=ConversationSentiment.POSITIVE,
        stage=ConversationStage.ENGAGED,
        analysisSummary="The contact asked for timing options.",
        status=DraftApprovalStatus.PENDING,
        createdAt=datetime.now(timezone.utc).isoformat(),
    )


class _FakeCursor:
    def __init__(self, db: dict) -> None:
        self.db = db
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query: str, params=()):
        normalized = " ".join(query.split()).lower()
        if normalized.startswith("insert into followup_drafts"):
            draft_id = params[0]
            payload_json = params[9]
            business_date = params[4]
            self.db["followup_drafts"][draft_id] = {
                "business_date": business_date,
                "payload_json": payload_json,
            }
            self._rows = []
            return
        if normalized.startswith("select payload_json from followup_drafts where draft_id"):
            row = self.db["followup_drafts"].get(params[0])
            self._rows = [(row["payload_json"],)] if row else []
            return
        if "select payload_json from followup_drafts where business_date = (select max(business_date)" in normalized:
            if not self.db["followup_drafts"]:
                self._rows = []
                return
            latest = max(row["business_date"] for row in self.db["followup_drafts"].values())
            self._rows = [
                (row["payload_json"],)
                for row in self.db["followup_drafts"].values()
                if row["business_date"] == latest
            ]
            return
        if normalized.startswith("select payload_json from followup_drafts where business_date ="):
            business_date = params[0]
            rows = [
                (row["payload_json"],)
                for row in self.db["followup_drafts"].values()
                if row["business_date"] == business_date
            ]
            self._rows = rows
            return
        raise AssertionError(f"Unhandled query in fake postgres backend: {query}")

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class _FakeConnection:
    def __init__(self, db: dict) -> None:
        self.db = db

    def cursor(self):
        return _FakeCursor(self.db)

    def commit(self):
        return None

    def close(self):
        return None


@pytest.fixture
def _tmp_env(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("REGISTRY_DIR", str(tmp_path / "registry"))


class TestPersistenceFactory:
    def test_file_backend_is_default(self, _tmp_env):
        backend = get_storage_backend()
        assert isinstance(backend, FileStorageBackend)

    def test_postgres_backend_selected_by_env(self, monkeypatch, _tmp_env):
        monkeypatch.setenv("STORAGE_BACKEND", "postgres")
        monkeypatch.setenv("DATABASE_URL", "postgresql://example")

        backend = get_storage_backend()

        assert isinstance(backend, PostgresStorageBackend)


class TestPersistenceBackends:
    def test_file_backend_round_trip(self, _tmp_env):
        backend = FileStorageBackend()
        draft = _build_followup("draft-file", "2026-03-09")

        backend.save_followup_draft(draft)
        loaded = backend.get_followup_draft("draft-file")

        assert loaded is not None
        assert loaded.draft_id == "draft-file"
        assert backend.list_followup_drafts(latest_only=True)[0].draft_id == "draft-file"

    def test_postgres_backend_followup_round_trip(self, monkeypatch, _tmp_env):
        fake_db = {"followup_drafts": {}}

        class _FakePsycopgModule:
            @staticmethod
            def connect(_dsn):
                return _FakeConnection(fake_db)

        monkeypatch.setattr(
            "persistence.postgres_store._load_psycopg",
            lambda: _FakePsycopgModule,
        )
        backend = PostgresStorageBackend(database_url="postgresql://example")

        day_one = _build_followup("draft-day-one", "2026-03-09")
        day_two = _build_followup("draft-day-two", "2026-03-10")

        backend.save_followup_draft(day_one)
        backend.save_followup_draft(day_two)

        loaded = backend.get_followup_draft("draft-day-one")
        latest = backend.list_followup_drafts(latest_only=True)
        by_date = backend.list_followup_drafts(business_date="2026-03-09")

        assert loaded is not None
        assert loaded.business_date == "2026-03-09"
        assert [draft.draft_id for draft in latest] == ["draft-day-two"]
        assert [draft.draft_id for draft in by_date] == ["draft-day-one"]
