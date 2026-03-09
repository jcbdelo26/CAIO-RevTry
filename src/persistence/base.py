"""Abstract persistence interface used by warm follow-up and shared safety state."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional

from models.schemas import (
    ContactConversationSummary,
    ConversationAnalysis,
    DailyBriefing,
    FollowUpDraft,
)


class StorageBackend(ABC):
    @abstractmethod
    def save_conversation_summary(self, summary: ContactConversationSummary) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_conversation_summary(self, contact_id: str) -> Optional[ContactConversationSummary]:
        raise NotImplementedError

    @abstractmethod
    def list_conversation_summaries(self) -> list[ContactConversationSummary]:
        raise NotImplementedError

    @abstractmethod
    def save_conversation_analysis(self, analysis: ConversationAnalysis) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_conversation_analysis(self, contact_id: str) -> Optional[ConversationAnalysis]:
        raise NotImplementedError

    @abstractmethod
    def list_conversation_analyses(self) -> list[ConversationAnalysis]:
        raise NotImplementedError

    @abstractmethod
    def save_followup_draft(self, draft: FollowUpDraft) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_followup_draft(self, draft_id: str) -> Optional[FollowUpDraft]:
        raise NotImplementedError

    @abstractmethod
    def list_followup_drafts(
        self,
        *,
        business_date: str | None = None,
        latest_only: bool = False,
    ) -> list[FollowUpDraft]:
        raise NotImplementedError

    @abstractmethod
    def save_daily_briefing(self, briefing: DailyBriefing) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_daily_briefing(self, briefing_date: str) -> Optional[DailyBriefing]:
        raise NotImplementedError

    @abstractmethod
    def list_daily_briefings(self) -> list[DailyBriefing]:
        raise NotImplementedError

    @abstractmethod
    def get_sent_hash(self, draft_hash: str) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def record_sent_hash(self, draft_hash: str, sent_at: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_dispatch_entries(self, *, channel: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def record_dispatch(self, contact_id: str, channel: str, draft_id: str, sent_at: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_rate_limit_counts(self, business_date: str) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    def save_rate_limit_counts(self, business_date: str, counts: dict[str, int]) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_circuit_breaker_state(
        self,
        integrations: Iterable[str],
    ) -> dict[str, dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def save_circuit_breaker_state(self, state: dict[str, dict[str, Any]]) -> None:
        raise NotImplementedError

    @abstractmethod
    def record_feedback_event(
        self,
        *,
        draft_id: str,
        channel: str,
        reason: str,
        payload: dict[str, Any],
    ) -> None:
        raise NotImplementedError
