"""Structured JSON trace logger for pipeline execution.

Logs are written to outputs/logs/ with one JSON file per pipeline run.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TraceLogger:
    """Accumulates trace events during a pipeline run and writes them to disk."""

    def __init__(self, task_id: str, agent: str) -> None:
        self.task_id = task_id
        self.agent = agent
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.events: list[dict[str, Any]] = []
        self.tools_called: list[str] = []
        self.vault_files_used: list[str] = []
        self.pages_fetched: int = 0

    def log_event(self, event_type: str, detail: dict[str, Any] | str) -> None:
        self.events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "detail": detail,
        })

    def log_tool_call(self, tool_name: str) -> None:
        if tool_name not in self.tools_called:
            self.tools_called.append(tool_name)

    def log_vault_file(self, vault_path: str) -> None:
        if vault_path not in self.vault_files_used:
            self.vault_files_used.append(vault_path)

    def log_page_fetch(self, count: int = 1) -> None:
        self.pages_fetched += count

    def log_error(self, error: str, context: dict[str, Any] | None = None) -> None:
        self.log_event("error", {"error": error, **(context or {})})

    def to_dict(self) -> dict[str, Any]:
        return {
            "taskId": self.task_id,
            "agent": self.agent,
            "startedAt": self.started_at,
            "completedAt": datetime.now(timezone.utc).isoformat(),
            "toolsCalled": self.tools_called,
            "vaultFilesUsed": self.vault_files_used,
            "pagesFetched": self.pages_fetched,
            "eventCount": len(self.events),
            "events": self.events,
        }

    def write(self) -> Path:
        outputs_dir = Path(os.environ.get("OUTPUTS_DIR", "outputs"))
        log_dir = outputs_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.task_id}_{self.agent}.json"
        path = log_dir / filename

        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path
