"""Shared business-time helpers for warm follow-up scheduling and daily limits."""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_BUSINESS_TIMEZONE = "America/Chicago"


def get_business_timezone_name() -> str:
    return os.environ.get("SCHEDULER_TIMEZONE", DEFAULT_BUSINESS_TIMEZONE)


def get_business_timezone() -> ZoneInfo:
    tz_name = get_business_timezone_name()
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def current_business_date(reference_time: datetime | None = None) -> str:
    reference_time = reference_time or datetime.now(timezone.utc)
    return reference_time.astimezone(get_business_timezone()).date().isoformat()


def parse_business_date(value: str) -> date:
    return date.fromisoformat(value)
