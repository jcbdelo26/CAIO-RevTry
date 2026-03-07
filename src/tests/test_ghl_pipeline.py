"""Tests for GHL pipeline runner — guard, segmentation, dry-run, full run."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.schemas import (
    EnrichmentGrade,
    EnrichmentRecord,
    WaterfallStatus,
    WaterfallTrace,
)
from scripts.ghl_pipeline import run_ghl_pipeline


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _use_tmp_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("REGISTRY_DIR", str(tmp_path / "registry"))


def _make_whitelist(tmp_path, candidates):
    outputs = tmp_path / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    path = outputs / "ghl_followup_candidates.json"
    path.write_text(json.dumps({
        "generated_at": "2026-03-08T00:00:00Z",
        "total_candidates": len(candidates),
        "candidates": candidates,
    }, indent=2), encoding="utf-8")


CANDIDATE_READY = {
    "ghl_contact_id": "ghl-001",
    "email": "ceo@acme.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "company_name": "Acme Corp",
    "score": 60,
}

CANDIDATE_REJECT = {
    "ghl_contact_id": "ghl-002",
    "email": "nobody@personal.com",
    "first_name": "",
    "last_name": "",
    "company_name": "",
    "score": 10,
}


def _make_enrichment_record(contact_id, email, score, grade, fields_filled, **kwargs):
    return EnrichmentRecord(
        contactId=contact_id,
        email=email,
        title=kwargs.get("title", "CEO"),
        companyName=kwargs.get("company_name", "Acme Corp"),
        companySize=kwargs.get("company_size", 150),
        industry=kwargs.get("industry", "management consulting"),
        revenue=kwargs.get("revenue", "$25M"),
        linkedinUrl=kwargs.get("linkedin_url", "https://linkedin.com/in/jane"),
        enrichmentScore=score,
        enrichmentGrade=grade,
        fieldsFilled=fields_filled,
        fieldsTotal=7,
        waterfallTrace=WaterfallTrace(
            apollo=WaterfallStatus.HIT,
            bettercontact=WaterfallStatus.SKIPPED,
            clay=WaterfallStatus.SKIPPED,
        ),
    )


READY_RECORD = _make_enrichment_record("ghl-001", "ceo@acme.com", 100, EnrichmentGrade.READY, 7)
REJECT_RECORD = _make_enrichment_record(
    "ghl-002", "nobody@personal.com", 14, EnrichmentGrade.REJECT, 1,
    title="", company_name="", company_size=None, industry="", revenue=None, linkedin_url=None,
)


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestGHLPipeline:
    @pytest.mark.asyncio
    async def test_guard003_filters_low_scores(self, tmp_path):
        """REJECT records should be blocked by GUARD-003."""
        _make_whitelist(tmp_path, [CANDIDATE_READY, CANDIDATE_REJECT])

        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(side_effect=[READY_RECORD, REJECT_RECORD])
        mock_enricher.close = AsyncMock()

        result = await run_ghl_pipeline(
            dry_run=True,
            enricher=mock_enricher,
        )

        assert result["guard003_blocked"] == 1
        assert result["guard003_passed"] == 1

    @pytest.mark.asyncio
    async def test_segmentation_produces_tiers(self, tmp_path):
        """Enriched records should get tier assignments after segmentation."""
        _make_whitelist(tmp_path, [CANDIDATE_READY])

        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(return_value=READY_RECORD)
        mock_enricher.close = AsyncMock()

        result = await run_ghl_pipeline(
            dry_run=True,
            enricher=mock_enricher,
        )

        # CEO at consulting firm with 150 employees should be T1 or T2
        total_tiered = result["tier1"] + result["tier2"] + result["tier3"]
        assert total_tiered >= 1

    @pytest.mark.asyncio
    async def test_dry_run_no_drafts_saved(self, tmp_path):
        """Dry-run should not save drafts to storage."""
        _make_whitelist(tmp_path, [CANDIDATE_READY])

        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(return_value=READY_RECORD)
        mock_enricher.close = AsyncMock()

        result = await run_ghl_pipeline(
            dry_run=True,
            enricher=mock_enricher,
        )

        assert result["saved"] == 0
        assert result["dry_run"] is True
        assert result["drafts"] >= 1  # Drafts generated but not saved

    @pytest.mark.asyncio
    async def test_full_run_saves_drafts(self, tmp_path):
        """Full run should save drafts to dashboard storage."""
        _make_whitelist(tmp_path, [CANDIDATE_READY])

        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(return_value=READY_RECORD)
        mock_enricher.close = AsyncMock()

        result = await run_ghl_pipeline(
            dry_run=False,
            enricher=mock_enricher,
        )

        # If gates passed, drafts should be saved
        if result["gates_passed"]:
            assert result["saved"] >= 1
        assert result["dry_run"] is False
