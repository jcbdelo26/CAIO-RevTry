"""Persistence backend selection helpers."""

from __future__ import annotations

import os

from .base import StorageBackend
from .file_store import FileStorageBackend
from .postgres_store import PostgresStorageBackend


def get_storage_backend_name() -> str:
    return os.environ.get("STORAGE_BACKEND", "file").strip().lower() or "file"


def resolve_database_url() -> str:
    return (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or "").strip()


def validate_storage_configuration(*, warm_only_mode: bool = False) -> None:
    backend = get_storage_backend_name()
    database_url = resolve_database_url()

    if backend not in {"file", "postgres"}:
        raise RuntimeError(f"Unsupported STORAGE_BACKEND '{backend}'")

    if backend == "postgres" and not database_url:
        raise RuntimeError("STORAGE_BACKEND=postgres requires DATABASE_URL or POSTGRES_URL")

    if warm_only_mode and backend != "postgres":
        raise RuntimeError("WARM_ONLY_MODE=true requires STORAGE_BACKEND=postgres")


def get_storage_backend() -> StorageBackend:
    backend = get_storage_backend_name()
    if backend == "postgres":
        return PostgresStorageBackend(database_url=resolve_database_url())
    return FileStorageBackend()
