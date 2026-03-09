"""Postgres-backed storage implementation for deployed warm-only mode."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterable, Optional

from models.schemas import (
    ContactConversationSummary,
    ConversationAnalysis,
    DailyBriefing,
    FollowUpDraft,
)

from .base import StorageBackend


def _load_psycopg():
    try:
        import psycopg
    except ModuleNotFoundError as exc:
        raise ImportError(
            "psycopg is required for STORAGE_BACKEND=postgres; install project dependencies first"
        ) from exc
    return psycopg


class PostgresStorageBackend(StorageBackend):
    def __init__(self, *, database_url: str) -> None:
        if not database_url:
            raise RuntimeError("PostgresStorageBackend requires a database URL")
        self.database_url = database_url

    @contextmanager
    def _connect(self):
        psycopg = _load_psycopg()
        conn = psycopg.connect(self.database_url, connect_timeout=5)
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _dump(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _decode_payload(raw: Any) -> dict[str, Any]:
        if isinstance(raw, str):
            return json.loads(raw)
        return raw

    def save_conversation_summary(self, summary: ContactConversationSummary) -> str:
        payload = summary.model_dump(by_alias=True)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conversation_summaries
                    (contact_id, ghl_contact_id, email, payload_json, scanned_at, updated_at)
                    VALUES (%s, %s, %s, %s::jsonb, %s, NOW())
                    ON CONFLICT (contact_id) DO UPDATE
                    SET ghl_contact_id = EXCLUDED.ghl_contact_id,
                        email = EXCLUDED.email,
                        payload_json = EXCLUDED.payload_json,
                        scanned_at = EXCLUDED.scanned_at,
                        updated_at = NOW()
                    """,
                    (
                        summary.contact_id,
                        summary.ghl_contact_id,
                        summary.email,
                        self._dump(payload),
                        summary.scanned_at,
                    ),
                )
            conn.commit()
        return f"postgres://conversation_summaries/{summary.contact_id}"

    def get_conversation_summary(self, contact_id: str) -> Optional[ContactConversationSummary]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload_json FROM conversation_summaries WHERE contact_id = %s",
                    (contact_id,),
                )
                row = cur.fetchone()
        if not row:
            return None
        return ContactConversationSummary.model_validate(self._decode_payload(row[0]))

    def list_conversation_summaries(self) -> list[ContactConversationSummary]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload_json FROM conversation_summaries ORDER BY updated_at DESC")
                rows = cur.fetchall()
        return [ContactConversationSummary.model_validate(self._decode_payload(row[0])) for row in rows]

    def save_conversation_analysis(self, analysis: ConversationAnalysis) -> str:
        payload = analysis.model_dump(by_alias=True)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conversation_analyses
                    (contact_id, source_conversation_id, payload_json, analyzed_at, updated_at)
                    VALUES (%s, %s, %s::jsonb, %s, NOW())
                    ON CONFLICT (contact_id) DO UPDATE
                    SET source_conversation_id = EXCLUDED.source_conversation_id,
                        payload_json = EXCLUDED.payload_json,
                        analyzed_at = EXCLUDED.analyzed_at,
                        updated_at = NOW()
                    """,
                    (
                        analysis.contact_id,
                        analysis.source_conversation_id,
                        self._dump(payload),
                        analysis.analyzed_at,
                    ),
                )
            conn.commit()
        return f"postgres://conversation_analyses/{analysis.contact_id}"

    def get_conversation_analysis(self, contact_id: str) -> Optional[ConversationAnalysis]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT payload_json FROM conversation_analyses WHERE contact_id = %s",
                    (contact_id,),
                )
                row = cur.fetchone()
        if not row:
            return None
        return ConversationAnalysis.model_validate(self._decode_payload(row[0]))

    def list_conversation_analyses(self) -> list[ConversationAnalysis]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload_json FROM conversation_analyses ORDER BY updated_at DESC")
                rows = cur.fetchall()
        return [ConversationAnalysis.model_validate(self._decode_payload(row[0])) for row in rows]

    def save_followup_draft(self, draft: FollowUpDraft) -> str:
        payload = draft.model_dump(by_alias=True)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO followup_drafts
                    (draft_id, contact_id, ghl_contact_id, source_conversation_id, business_date, generation_run_id,
                     status, subject, body, payload_json, approved_at, rejected_at, rejection_reason, dispatched_at,
                     send_failed_at, dispatch_error, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (draft_id) DO UPDATE
                    SET ghl_contact_id = EXCLUDED.ghl_contact_id,
                        source_conversation_id = EXCLUDED.source_conversation_id,
                        business_date = EXCLUDED.business_date,
                        generation_run_id = EXCLUDED.generation_run_id,
                        status = EXCLUDED.status,
                        subject = EXCLUDED.subject,
                        body = EXCLUDED.body,
                        payload_json = EXCLUDED.payload_json,
                        approved_at = EXCLUDED.approved_at,
                        rejected_at = EXCLUDED.rejected_at,
                        rejection_reason = EXCLUDED.rejection_reason,
                        dispatched_at = EXCLUDED.dispatched_at,
                        send_failed_at = EXCLUDED.send_failed_at,
                        dispatch_error = EXCLUDED.dispatch_error,
                        created_at = EXCLUDED.created_at,
                        updated_at = NOW()
                    """,
                    (
                        draft.draft_id,
                        draft.contact_id,
                        draft.ghl_contact_id,
                        draft.source_conversation_id,
                        draft.business_date,
                        draft.generation_run_id,
                        draft.status.value,
                        draft.subject,
                        draft.body,
                        self._dump(payload),
                        draft.approved_at,
                        draft.rejected_at,
                        draft.rejection_reason,
                        draft.dispatched_at,
                        draft.send_failed_at,
                        draft.dispatch_error,
                        draft.created_at,
                    ),
                )
            conn.commit()
        return f"postgres://followup_drafts/{draft.draft_id}"

    def get_followup_draft(self, draft_id: str) -> Optional[FollowUpDraft]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload_json FROM followup_drafts WHERE draft_id = %s", (draft_id,))
                row = cur.fetchone()
        if not row:
            return None
        return FollowUpDraft.model_validate(self._decode_payload(row[0]))

    def list_followup_drafts(
        self,
        *,
        business_date: str | None = None,
        latest_only: bool = False,
    ) -> list[FollowUpDraft]:
        query = "SELECT payload_json FROM followup_drafts"
        params: tuple[Any, ...] = ()
        if business_date:
            query += " WHERE business_date = %s"
            params = (business_date,)
        elif latest_only:
            query += " WHERE business_date = (SELECT MAX(business_date) FROM followup_drafts)"
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
        return [FollowUpDraft.model_validate(self._decode_payload(row[0])) for row in rows]

    def save_daily_briefing(self, briefing: DailyBriefing) -> str:
        payload = briefing.model_dump(by_alias=True)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO daily_briefings (date, payload_json, generated_at)
                    VALUES (%s, %s::jsonb, %s)
                    ON CONFLICT (date) DO UPDATE
                    SET payload_json = EXCLUDED.payload_json,
                        generated_at = EXCLUDED.generated_at
                    """,
                    (briefing.date, self._dump(payload), briefing.generated_at),
                )
            conn.commit()
        return f"postgres://daily_briefings/{briefing.date}"

    def get_daily_briefing(self, briefing_date: str) -> Optional[DailyBriefing]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload_json FROM daily_briefings WHERE date = %s", (briefing_date,))
                row = cur.fetchone()
        if not row:
            return None
        return DailyBriefing.model_validate(self._decode_payload(row[0]))

    def list_daily_briefings(self) -> list[DailyBriefing]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT payload_json FROM daily_briefings ORDER BY date DESC")
                rows = cur.fetchall()
        return [DailyBriefing.model_validate(self._decode_payload(row[0])) for row in rows]

    def get_sent_hash(self, draft_hash: str) -> Optional[str]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT sent_at FROM sent_hashes WHERE draft_hash = %s", (draft_hash,))
                row = cur.fetchone()
        return row[0] if row else None

    def record_sent_hash(self, draft_hash: str, sent_at: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sent_hashes (draft_hash, sent_at)
                    VALUES (%s, %s)
                    ON CONFLICT (draft_hash) DO UPDATE SET sent_at = EXCLUDED.sent_at
                    """,
                    (draft_hash, sent_at),
                )
            conn.commit()

    def list_dispatch_entries(self, *, channel: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT contact_id, channel, draft_id, sent_at FROM dispatch_log"
        params: tuple[Any, ...] = ()
        if channel:
            query += " WHERE channel = %s"
            params = (channel,)
        query += " ORDER BY sent_at DESC"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                rows = cur.fetchall()
        return [
            {
                "contact_id": row[0],
                "channel": row[1],
                "draft_id": row[2],
                "sent_at": row[3],
            }
            for row in rows
        ]

    def record_dispatch(self, contact_id: str, channel: str, draft_id: str, sent_at: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO dispatch_log (contact_id, channel, draft_id, sent_at) VALUES (%s, %s, %s, %s)",
                    (contact_id, channel, draft_id, sent_at),
                )
            conn.commit()

    def load_rate_limit_counts(self, business_date: str) -> dict[str, int]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT channel, count FROM rate_limit_counters WHERE business_date = %s",
                    (business_date,),
                )
                rows = cur.fetchall()
        return {row[0]: row[1] for row in rows}

    def save_rate_limit_counts(self, business_date: str, counts: dict[str, int]) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                for channel, count in counts.items():
                    cur.execute(
                        """
                        INSERT INTO rate_limit_counters (business_date, channel, count, updated_at)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (business_date, channel) DO UPDATE
                        SET count = EXCLUDED.count,
                            updated_at = NOW()
                        """,
                        (business_date, channel, count),
                    )
            conn.commit()

    def load_circuit_breaker_state(
        self,
        integrations: Iterable[str],
    ) -> dict[str, dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT integration, state, consecutive_failures, tripped_at, last_failure FROM circuit_breakers"
                )
                rows = cur.fetchall()
        data = {
            row[0]: {
                "state": row[1],
                "consecutive_failures": row[2],
                "tripped_at": row[3],
                "last_failure": row[4],
            }
            for row in rows
        }
        for integration in integrations:
            data.setdefault(
                integration,
                {
                    "state": "CLOSED",
                    "consecutive_failures": 0,
                    "tripped_at": None,
                    "last_failure": None,
                },
            )
        return data

    def save_circuit_breaker_state(self, state: dict[str, dict[str, Any]]) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                for integration, entry in state.items():
                    cur.execute(
                        """
                        INSERT INTO circuit_breakers (integration, state, consecutive_failures, tripped_at, last_failure)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (integration) DO UPDATE
                        SET state = EXCLUDED.state,
                            consecutive_failures = EXCLUDED.consecutive_failures,
                            tripped_at = EXCLUDED.tripped_at,
                            last_failure = EXCLUDED.last_failure
                        """,
                        (
                            integration,
                            entry["state"],
                            entry["consecutive_failures"],
                            entry["tripped_at"],
                            entry["last_failure"],
                        ),
                    )
            conn.commit()

    def record_feedback_event(
        self,
        *,
        draft_id: str,
        channel: str,
        reason: str,
        payload: dict[str, Any],
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO feedback_events (draft_id, channel, reason, created_at, payload_json)
                    VALUES (%s, %s, %s, NOW(), %s::jsonb)
                    """,
                    (draft_id, channel, reason, self._dump(payload)),
                )
            conn.commit()
