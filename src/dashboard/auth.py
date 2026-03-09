"""Dashboard authentication and deployed-mode helpers."""

from __future__ import annotations

import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials


security = HTTPBasic(auto_error=False)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def is_deployed_environment() -> bool:
    return bool(os.environ.get("VERCEL"))


def is_dashboard_auth_enabled() -> bool:
    return _env_bool("DASHBOARD_AUTH_ENABLED", default=is_deployed_environment())


def is_warm_only_mode() -> bool:
    return _env_bool("WARM_ONLY_MODE", default=is_deployed_environment())


def require_dashboard_auth(
    credentials: HTTPBasicCredentials | None = Depends(security),
) -> None:
    if not is_dashboard_auth_enabled():
        return

    expected_user = os.environ.get("DASHBOARD_BASIC_AUTH_USER", "")
    expected_pass = os.environ.get("DASHBOARD_BASIC_AUTH_PASS", "")

    username = credentials.username if credentials else ""
    password = credentials.password if credentials else ""

    valid_user = secrets.compare_digest(username, expected_user)
    valid_pass = secrets.compare_digest(password, expected_pass)

    if not (valid_user and valid_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Dashboard authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
