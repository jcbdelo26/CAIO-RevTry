"""Tests for 3-layer dedup — hash, contact window, clean pass."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from pipeline.dedup import (
    check_contact_window,
    check_dedup,
    check_hash_dedup,
    compute_draft_hash,
    record_dispatch,
    record_hash,
)


@pytest.fixture(autouse=True)
def _use_tmp_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("REGISTRY_DIR", str(tmp_path / "registry"))


class TestHashDedup:
    def test_clean_pass(self):
        h = compute_draft_hash("c1", "Hello", "Body text", "instantly")
        is_dup, reason = check_hash_dedup(h)
        assert is_dup is False

    def test_duplicate_detected(self):
        h = compute_draft_hash("c1", "Hello", "Body text", "instantly")
        record_hash(h)
        is_dup, reason = check_hash_dedup(h)
        assert is_dup is True
        assert "Duplicate hash" in reason

    def test_different_content_passes(self):
        h1 = compute_draft_hash("c1", "Hello", "Body A", "instantly")
        h2 = compute_draft_hash("c1", "Hello", "Body B", "instantly")
        record_hash(h1)
        is_dup, _ = check_hash_dedup(h2)
        assert is_dup is False


class TestContactWindow:
    def test_clean_pass(self):
        is_dup, reason = check_contact_window("c1", "instantly")
        assert is_dup is False

    def test_recent_dispatch_blocks(self):
        record_dispatch("c1", "instantly", "draft-1")
        is_dup, reason = check_contact_window("c1", "instantly")
        assert is_dup is True
        assert "within" in reason

    def test_different_channel_passes(self):
        record_dispatch("c1", "instantly", "draft-1")
        is_dup, _ = check_contact_window("c1", "ghl")
        assert is_dup is False

    def test_different_contact_passes(self):
        record_dispatch("c1", "instantly", "draft-1")
        is_dup, _ = check_contact_window("c2", "instantly")
        assert is_dup is False


class TestCombinedDedup:
    @pytest.mark.asyncio
    async def test_clean_pass(self):
        is_dup, reason = await check_dedup("c1", "instantly", "Subj", "Body")
        assert is_dup is False

    @pytest.mark.asyncio
    async def test_hash_blocks(self):
        h = compute_draft_hash("c1", "Subj", "Body", "instantly")
        record_hash(h)
        is_dup, reason = await check_dedup("c1", "instantly", "Subj", "Body")
        assert is_dup is True
