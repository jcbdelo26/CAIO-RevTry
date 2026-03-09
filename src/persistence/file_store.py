"""File-backed storage implementation for local development."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Optional, TypeVar

from models.schemas import (
    ContactConversationSummary,
    ConversationAnalysis,
    DailyBriefing,
    FollowUpDraft,
)

from .base import StorageBackend

T = TypeVar("T")


class FileStorageBackend(StorageBackend):
    def __init__(self, *, outputs_dir: str | None = None, registry_dir: str | None = None) -> None:
        self._outputs_dir = Path(outputs_dir or os.environ.get("OUTPUTS_DIR", "outputs"))
        self._registry_dir = Path(registry_dir or os.environ.get("REGISTRY_DIR", "registry"))

    def _ensure_dir(self, path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _indexed_dir(self, subdir: str) -> Path:
        return self._ensure_dir(self._outputs_dir / subdir)

    def _indexed_path(self, subdir: str, item_id: str) -> Path:
        return self._indexed_dir(subdir) / f"{item_id}.json"

    def _index_path(self, subdir: str) -> Path:
        return self._indexed_dir(subdir) / "index.json"

    def _load_index(self, subdir: str) -> dict[str, str]:
        path = self._index_path(subdir)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def _save_index(self, subdir: str, index: dict[str, str]) -> None:
        self._index_path(subdir).write_text(
            json.dumps(index, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _save_indexed_model(self, subdir: str, item_id: str, payload: dict[str, Any]) -> str:
        path = self._indexed_path(subdir, item_id)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        index = self._load_index(subdir)
        index[item_id] = str(path)
        self._save_index(subdir, index)
        return str(path)

    def _get_indexed_model(self, subdir: str, item_id: str, model_cls: type[T]) -> Optional[T]:
        path = self._indexed_path(subdir, item_id)
        if not path.exists():
            return None
        return model_cls.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def _list_indexed_models(self, subdir: str, model_cls: type[T]) -> list[T]:
        directory = self._indexed_dir(subdir)
        index_path = directory / "index.json"
        if index_path.exists():
            index = json.loads(index_path.read_text(encoding="utf-8"))
            paths = [Path(raw) for raw in index.values()]
        else:
            paths = [path for path in directory.glob("*.json") if path.name != "index.json"]

        items: list[T] = []
        for path in paths:
            if not path.exists() or path.name == "index.json":
                continue
            items.append(model_cls.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        return items

    def save_conversation_summary(self, summary: ContactConversationSummary) -> str:
        return self._save_indexed_model("conversations", summary.contact_id, summary.model_dump(by_alias=True))

    def get_conversation_summary(self, contact_id: str) -> Optional[ContactConversationSummary]:
        return self._get_indexed_model("conversations", contact_id, ContactConversationSummary)

    def list_conversation_summaries(self) -> list[ContactConversationSummary]:
        return self._list_indexed_models("conversations", ContactConversationSummary)

    def save_conversation_analysis(self, analysis: ConversationAnalysis) -> str:
        return self._save_indexed_model(
            "conversation_analysis",
            analysis.contact_id,
            analysis.model_dump(by_alias=True),
        )

    def get_conversation_analysis(self, contact_id: str) -> Optional[ConversationAnalysis]:
        return self._get_indexed_model("conversation_analysis", contact_id, ConversationAnalysis)

    def list_conversation_analyses(self) -> list[ConversationAnalysis]:
        return self._list_indexed_models("conversation_analysis", ConversationAnalysis)

    def save_followup_draft(self, draft: FollowUpDraft) -> str:
        return self._save_indexed_model("followups", draft.draft_id, draft.model_dump(by_alias=True))

    def get_followup_draft(self, draft_id: str) -> Optional[FollowUpDraft]:
        return self._get_indexed_model("followups", draft_id, FollowUpDraft)

    def list_followup_drafts(
        self,
        *,
        business_date: str | None = None,
        latest_only: bool = False,
    ) -> list[FollowUpDraft]:
        drafts = self._list_indexed_models("followups", FollowUpDraft)
        if business_date:
            drafts = [draft for draft in drafts if draft.business_date == business_date]
        elif latest_only and drafts:
            latest = max(draft.business_date for draft in drafts)
            drafts = [draft for draft in drafts if draft.business_date == latest]
        return drafts

    def save_daily_briefing(self, briefing: DailyBriefing) -> str:
        path = self._ensure_dir(self._outputs_dir / "briefings") / f"{briefing.date}.json"
        path.write_text(
            json.dumps(briefing.model_dump(by_alias=True), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return str(path)

    def get_daily_briefing(self, briefing_date: str) -> Optional[DailyBriefing]:
        path = self._ensure_dir(self._outputs_dir / "briefings") / f"{briefing_date}.json"
        if not path.exists():
            return None
        return DailyBriefing.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list_daily_briefings(self) -> list[DailyBriefing]:
        directory = self._ensure_dir(self._outputs_dir / "briefings")
        briefings: list[DailyBriefing] = []
        for path in sorted(directory.glob("*.json")):
            briefings.append(DailyBriefing.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        return briefings

    def _registry_path(self, filename: str) -> Path:
        self._ensure_dir(self._registry_dir)
        return self._registry_dir / filename

    def get_sent_hash(self, draft_hash: str) -> Optional[str]:
        path = self._registry_path("sent_hashes.json")
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data.get(draft_hash)
        return None

    def record_sent_hash(self, draft_hash: str, sent_at: str) -> None:
        path = self._registry_path("sent_hashes.json")
        if path.exists():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            data = loaded if isinstance(loaded, dict) else {}
        else:
            data = {}
        data[draft_hash] = sent_at
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def list_dispatch_entries(self, *, channel: str | None = None) -> list[dict[str, Any]]:
        path = self._registry_path("dispatch_log.json")
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data if isinstance(data, list) else []
        if channel is not None:
            entries = [entry for entry in entries if entry.get("channel") == channel]
        return entries

    def record_dispatch(self, contact_id: str, channel: str, draft_id: str, sent_at: str) -> None:
        path = self._registry_path("dispatch_log.json")
        entries = self.list_dispatch_entries()
        entries.append(
            {
                "contact_id": contact_id,
                "channel": channel,
                "draft_id": draft_id,
                "sent_at": sent_at,
            }
        )
        path.write_text(json.dumps(entries, indent=2), encoding="utf-8")

    def load_rate_limit_counts(self, business_date: str) -> dict[str, int]:
        path = self._registry_path(f"dispatch_counter_{business_date}.json")
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    def save_rate_limit_counts(self, business_date: str, counts: dict[str, int]) -> None:
        path = self._registry_path(f"dispatch_counter_{business_date}.json")
        path.write_text(json.dumps(counts, indent=2), encoding="utf-8")

    def load_circuit_breaker_state(
        self,
        integrations: Iterable[str],
    ) -> dict[str, dict[str, Any]]:
        path = self._registry_path("circuit_breaker_state.json")
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = {}
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
        path = self._registry_path("circuit_breaker_state.json")
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def record_feedback_event(
        self,
        *,
        draft_id: str,
        channel: str,
        reason: str,
        payload: dict[str, Any],
    ) -> None:
        directory = self._ensure_dir(self._registry_dir / "pending_feedback")
        path = directory / f"{draft_id}.md"
        title = "Warm Follow-Up Rejection Feedback" if channel == "warm_followup" else "Feedback Event"
        path.write_text(
            f"# {title}: {draft_id}\n\n"
            f"- **Channel**: {channel}\n"
            f"- **Reason**: {reason}\n"
            f"- **Payload**: `{json.dumps(payload, ensure_ascii=False)}`\n",
            encoding="utf-8",
        )
