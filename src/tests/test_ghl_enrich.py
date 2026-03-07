"""Tests for GHL follow-up enrichment script — whitelist, identity, dry-run."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.ghl_enrich import (
    enrich_candidates,
    load_whitelist,
    verify_identity,
    write_enrichment_report,
)
from models.schemas import EnrichmentGrade, EnrichmentRecord, WaterfallStatus, WaterfallTrace


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _use_tmp_outputs(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))


def _make_whitelist(tmp_path, candidates):
    """Write a whitelist JSON file for testing."""
    outputs = tmp_path / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    path = outputs / "ghl_followup_candidates.json"
    path.write_text(json.dumps({
        "generated_at": "2026-03-08T00:00:00Z",
        "total_candidates": len(candidates),
        "candidates": candidates,
    }, indent=2), encoding="utf-8")
    return path


SAMPLE_CANDIDATE = {
    "ghl_contact_id": "ghl-001",
    "email": "jane@acme.com",
    "first_name": "Jane",
    "last_name": "Doe",
    "company_name": "Acme Corp",
    "score": 60,
}

SAMPLE_ENRICHMENT_RECORD = EnrichmentRecord(
    contactId="ghl-001",
    email="jane@acme.com",
    title="CEO",
    companyName="Acme Corp",
    companySize=150,
    industry="Technology",
    revenue="$25M",
    linkedinUrl="https://linkedin.com/in/jane",
    enrichmentScore=100,
    enrichmentGrade=EnrichmentGrade.READY,
    fieldsFilled=7,
    fieldsTotal=7,
    waterfallTrace=WaterfallTrace(
        apollo=WaterfallStatus.HIT,
        bettercontact=WaterfallStatus.SKIPPED,
        clay=WaterfallStatus.SKIPPED,
    ),
)


# ── Whitelist Loading ──────────────────────────────────────────────────────────


class TestLoadWhitelist:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Whitelist not found"):
            load_whitelist(str(tmp_path / "outputs"))

    def test_empty_candidates_raises(self, tmp_path):
        _make_whitelist(tmp_path, [])
        with pytest.raises(ValueError, match="Whitelist is empty"):
            load_whitelist(str(tmp_path / "outputs"))

    def test_valid_whitelist_loads(self, tmp_path):
        _make_whitelist(tmp_path, [SAMPLE_CANDIDATE])
        result = load_whitelist(str(tmp_path / "outputs"))
        assert len(result) == 1
        assert result[0]["ghl_contact_id"] == "ghl-001"
        assert result[0]["email"] == "jane@acme.com"


# ── Identity Verification ─────────────────────────────────────────────────────


class TestIdentityVerification:
    def test_same_domain_verified(self):
        assert verify_identity("jane@acme.com", "john@acme.com") is True

    def test_different_domain_mismatch(self):
        assert verify_identity("jane@acme.com", "jane@other.com") is False

    def test_no_enriched_email_verified(self):
        assert verify_identity("jane@acme.com", None) is True

    def test_no_input_email_verified(self):
        assert verify_identity("", "jane@acme.com") is True


# ── Enrichment ─────────────────────────────────────────────────────────────────


class TestEnrichCandidates:
    @pytest.mark.asyncio
    async def test_enrich_single_candidate(self):
        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(return_value=SAMPLE_ENRICHMENT_RECORD)
        mock_enricher.close = AsyncMock()

        results = await enrich_candidates(
            [SAMPLE_CANDIDATE],
            commit=False,
            enricher=mock_enricher,
        )

        assert len(results) == 1
        assert results[0]["enrichment_score"] == 100
        assert results[0]["enrichment_grade"] == "READY"
        assert results[0]["identity_check"] == "VERIFIED"
        assert results[0]["ghl_writeback"] == "SKIPPED"  # dry-run

    @pytest.mark.asyncio
    async def test_identity_mismatch_skips_writeback(self):
        mismatched_record = EnrichmentRecord(
            contactId="ghl-001",
            email="jane@different.com",  # Different domain!
            title="CEO",
            companyName="Acme Corp",
            companySize=None,
            industry=None,
            revenue=None,
            linkedinUrl=None,
            enrichmentScore=43,
            enrichmentGrade=EnrichmentGrade.REJECT,
            fieldsFilled=3,
            fieldsTotal=7,
            waterfallTrace=WaterfallTrace(
                apollo=WaterfallStatus.HIT,
                bettercontact=WaterfallStatus.SKIPPED,
                clay=WaterfallStatus.SKIPPED,
            ),
        )
        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(return_value=mismatched_record)
        mock_enricher.close = AsyncMock()

        mock_ghl = MagicMock()
        mock_ghl.upsert_contact = AsyncMock()
        mock_ghl.close = AsyncMock()

        results = await enrich_candidates(
            [SAMPLE_CANDIDATE],
            commit=True,
            enricher=mock_enricher,
            ghl=mock_ghl,
        )

        assert results[0]["identity_check"] == "IDENTITY_MISMATCH"
        assert results[0]["ghl_writeback"] == "BLOCKED_IDENTITY_MISMATCH"
        mock_ghl.upsert_contact.assert_not_called()

    @pytest.mark.asyncio
    async def test_dry_run_no_ghl_writes(self):
        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(return_value=SAMPLE_ENRICHMENT_RECORD)
        mock_enricher.close = AsyncMock()

        mock_ghl = MagicMock()
        mock_ghl.upsert_contact = AsyncMock()
        mock_ghl.close = AsyncMock()

        results = await enrich_candidates(
            [SAMPLE_CANDIDATE],
            commit=False,
            enricher=mock_enricher,
            ghl=mock_ghl,
        )

        assert results[0]["ghl_writeback"] == "SKIPPED"
        mock_ghl.upsert_contact.assert_not_called()

    @pytest.mark.asyncio
    async def test_commit_writes_to_ghl(self):
        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(return_value=SAMPLE_ENRICHMENT_RECORD)
        mock_enricher.close = AsyncMock()

        mock_ghl = MagicMock()
        mock_ghl.upsert_contact = AsyncMock()
        mock_ghl.close = AsyncMock()

        results = await enrich_candidates(
            [SAMPLE_CANDIDATE],
            commit=True,
            enricher=mock_enricher,
            ghl=mock_ghl,
        )

        assert results[0]["ghl_writeback"] == "WRITTEN"
        mock_ghl.upsert_contact.assert_called_once()
        call_kwargs = mock_ghl.upsert_contact.call_args
        assert call_kwargs.kwargs.get("email") or call_kwargs[1].get("email") or "jane@acme.com" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_limit_flag(self):
        candidates = [
            {**SAMPLE_CANDIDATE, "ghl_contact_id": f"ghl-{i}", "email": f"user{i}@acme.com"}
            for i in range(5)
        ]
        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(return_value=SAMPLE_ENRICHMENT_RECORD)
        mock_enricher.close = AsyncMock()

        # Pass only first 2 (simulating --limit 2 from the caller)
        results = await enrich_candidates(
            candidates[:2],
            commit=False,
            enricher=mock_enricher,
        )

        assert len(results) == 2
        assert mock_enricher.enrich.call_count == 2


# ── Report Writing ─────────────────────────────────────────────────────────────


class TestReportWriting:
    def test_writes_report_file(self, tmp_path):
        results = [
            {
                "ghl_contact_id": "ghl-001",
                "email": "jane@acme.com",
                "enrichment_score": 100,
                "enrichment_grade": "READY",
                "fields_filled": 7,
                "fields_total": 7,
                "apollo_status": "HIT",
                "identity_check": "VERIFIED",
                "ghl_writeback": "SKIPPED",
                "enriched_data": {"company_name": "Acme Corp", "title": "CEO"},
            }
        ]
        outputs_dir = str(tmp_path / "outputs")
        path = write_enrichment_report(results, commit=False, outputs_dir=outputs_dir)
        assert Path(path).exists()
        content = Path(path).read_text(encoding="utf-8")
        assert "jane@acme.com" in content
        assert "READY" in content
        assert "DRY RUN" in content
