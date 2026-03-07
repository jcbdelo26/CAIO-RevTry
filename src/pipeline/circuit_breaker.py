"""Circuit Breaker — trips on 3 consecutive failures per integration.

States: CLOSED (normal) → OPEN (tripped) → HALF_OPEN (testing)
Recovery: HALF_OPEN after 30-minute cooldown → single test request
  - Test succeeds → CLOSED
  - Test fails → OPEN (reset cooldown timer)

File state: registry/circuit_breaker_state.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FAILURE_THRESHOLD = 3
COOLDOWN_SECONDS = 1800  # 30 minutes


def _state_path() -> Path:
    registry = Path(os.environ.get("REGISTRY_DIR", "registry"))
    registry.mkdir(parents=True, exist_ok=True)
    return registry / "circuit_breaker_state.json"


def _default_entry() -> dict[str, Any]:
    return {
        "state": "CLOSED",
        "consecutive_failures": 0,
        "tripped_at": None,
        "last_failure": None,
    }


class CircuitBreaker:
    """File-backed circuit breaker for outbound integrations."""

    INTEGRATIONS = ("instantly", "ghl", "heyreach", "apollo")

    def __init__(self, state_path: Path | None = None):
        self._path = state_path or _state_path()
        self._state = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if self._path.exists():
            data = json.loads(self._path.read_text(encoding="utf-8"))
            # Ensure all integrations are present
            for key in self.INTEGRATIONS:
                if key not in data:
                    data[key] = _default_entry()
            return data
        return {key: _default_entry() for key in self.INTEGRATIONS}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")

    def is_open(self, integration: str) -> bool:
        """Return True if the circuit is OPEN (tripped) and not yet in cooldown."""
        entry = self._state.get(integration, _default_entry())
        if entry["state"] == "CLOSED":
            return False
        if entry["state"] == "HALF_OPEN":
            return False  # Allow one test request
        # OPEN — check cooldown
        if entry["tripped_at"]:
            tripped = datetime.fromisoformat(entry["tripped_at"])
            elapsed = (datetime.now(timezone.utc) - tripped).total_seconds()
            if elapsed >= COOLDOWN_SECONDS:
                # Transition to HALF_OPEN
                entry["state"] = "HALF_OPEN"
                self._save()
                return False
        return True

    def get_state(self, integration: str) -> str:
        """Return current state: CLOSED, OPEN, or HALF_OPEN."""
        entry = self._state.get(integration, _default_entry())
        # Check for cooldown transition
        if entry["state"] == "OPEN" and entry["tripped_at"]:
            tripped = datetime.fromisoformat(entry["tripped_at"])
            elapsed = (datetime.now(timezone.utc) - tripped).total_seconds()
            if elapsed >= COOLDOWN_SECONDS:
                entry["state"] = "HALF_OPEN"
                self._save()
        return entry["state"]

    def record_success(self, integration: str) -> None:
        """Record a successful call — reset to CLOSED."""
        entry = self._state.setdefault(integration, _default_entry())
        entry["state"] = "CLOSED"
        entry["consecutive_failures"] = 0
        entry["tripped_at"] = None
        self._save()

    def record_failure(self, integration: str) -> None:
        """Record a failed call — increment failures, trip if threshold reached."""
        entry = self._state.setdefault(integration, _default_entry())
        entry["consecutive_failures"] += 1
        entry["last_failure"] = datetime.now(timezone.utc).isoformat()

        if entry["consecutive_failures"] >= FAILURE_THRESHOLD:
            entry["state"] = "OPEN"
            entry["tripped_at"] = datetime.now(timezone.utc).isoformat()

        self._save()

    def trip_all(self) -> None:
        """Emergency stop — trip all integrations immediately."""
        now = datetime.now(timezone.utc).isoformat()
        for key in self._state:
            self._state[key]["state"] = "OPEN"
            self._state[key]["tripped_at"] = now
        self._save()

    def get_all_states(self) -> dict[str, str]:
        """Return state for all integrations."""
        return {k: self.get_state(k) for k in self._state}

    async def call(self, integration: str, func, *args, **kwargs) -> Any:
        """Wrap an async dispatch call with circuit breaker protection."""
        if self.is_open(integration):
            raise RuntimeError(f"Circuit breaker OPEN for {integration}")

        try:
            result = await func(*args, **kwargs)
            self.record_success(integration)
            return result
        except Exception as e:
            self.record_failure(integration)
            raise
