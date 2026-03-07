"""Tests for dashboard endpoints — filters, batch actions."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _use_tmp_outputs(tmp_path, monkeypatch):
    """Point OUTPUTS_DIR and REGISTRY_DIR to tmp_path for isolation."""
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("REGISTRY_DIR", str(tmp_path / "registry"))


@pytest.fixture()
def client():
    from dashboard.app import app
    return TestClient(app)


@pytest.fixture()
def seeded_drafts(tmp_path):
    """Create a few test drafts on disk."""
    drafts_dir = tmp_path / "outputs" / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)

    index = {}
    for i, (tier, status, channel) in enumerate([
        ("1", "PENDING", "instantly"),
        ("2", "PENDING", "ghl"),
        ("1", "APPROVED", "instantly"),
        ("3", "REJECTED", "heyreach"),
    ]):
        draft_id = f"test-draft-{i}"
        draft_data = {
            "draftId": draft_id,
            "contactId": f"contact{i}@acme.com",
            "icpTier": tier,
            "angleId": "ai_executive_briefing",
            "subject": f"Test subject {i} for Acme",
            "body": f"Hi Contact{i},\n\nTest body.\n\nBest,\nChris",
            "channel": channel,
            "bookingLink": "https://caio.cx/ai-exec-briefing-call",
            "status": status,
            "createdAt": "2026-03-07T00:00:00Z",
            "approvedAt": "2026-03-07T01:00:00Z" if status == "APPROVED" else None,
            "rejectedAt": "2026-03-07T01:00:00Z" if status == "REJECTED" else None,
            "rejectionReason": "test reason" if status == "REJECTED" else None,
        }
        path = drafts_dir / f"{draft_id}.json"
        path.write_text(json.dumps(draft_data, indent=2), encoding="utf-8")
        index[draft_id] = str(path)

    (drafts_dir / "index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8"
    )
    return list(index.keys())


class TestDashboardLoads:
    def test_empty_dashboard(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "No drafts" in resp.text

    def test_dashboard_with_drafts(self, client, seeded_drafts):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "test-draft-0" in resp.text or "contact0@acme.com" in resp.text


class TestFilters:
    def test_filter_by_tier(self, client, seeded_drafts):
        resp = client.get("/?tier=1")
        assert resp.status_code == 200
        # Tier 1 drafts present, Tier 2/3 absent
        assert "contact0@acme.com" in resp.text  # Tier 1
        assert "contact1@acme.com" not in resp.text  # Tier 2

    def test_filter_by_status(self, client, seeded_drafts):
        resp = client.get("/?status=APPROVED")
        assert resp.status_code == 200
        assert "contact2@acme.com" in resp.text  # APPROVED
        assert "contact0@acme.com" not in resp.text  # PENDING

    def test_filter_by_channel(self, client, seeded_drafts):
        resp = client.get("/?channel=ghl")
        assert resp.status_code == 200
        assert "contact1@acme.com" in resp.text  # GHL
        assert "contact0@acme.com" not in resp.text  # Instantly

    def test_search(self, client, seeded_drafts):
        resp = client.get("/?search=contact1")
        assert resp.status_code == 200
        assert "contact1@acme.com" in resp.text
        assert "contact0@acme.com" not in resp.text


class TestBatchActions:
    @patch("dashboard.app.push_approved_draft_to_ghl", new_callable=AsyncMock)
    def test_batch_approve_empty(self, mock_ghl, client):
        mock_ghl.return_value = {"status": "pushed", "ghl_contact_id": "", "ghl_task_id": ""}
        resp = client.post(
            "/drafts/batch/approve",
            data={"draft_ids": ""},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_batch_reject_empty(self, client):
        resp = client.post(
            "/drafts/batch/reject",
            data={"draft_ids": "", "reason": "test"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
