"""Unit tests for waterfall enrichment."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from models.schemas import EnrichmentGrade, WaterfallStatus
from integrations.waterfall import (
    WaterfallEnricher,
    _compute_grade,
    _extract_fields,
    ENRICHABLE_FIELDS,
)


# ── Grade Computation ─────────────────────────────────────────────────────────

class TestComputeGrade:
    def test_ready(self):
        assert _compute_grade(100) == EnrichmentGrade.READY
        assert _compute_grade(90) == EnrichmentGrade.READY

    def test_partial(self):
        assert _compute_grade(89) == EnrichmentGrade.PARTIAL
        assert _compute_grade(70) == EnrichmentGrade.PARTIAL

    def test_minimal(self):
        assert _compute_grade(69) == EnrichmentGrade.MINIMAL
        assert _compute_grade(50) == EnrichmentGrade.MINIMAL

    def test_reject(self):
        assert _compute_grade(49) == EnrichmentGrade.REJECT
        assert _compute_grade(0) == EnrichmentGrade.REJECT


# ── Field Extraction ──────────────────────────────────────────────────────────

class TestExtractFields:
    def test_full_apollo_response(self):
        raw = {
            "email": "jane@acme.com",
            "title": "CEO",
            "organization_name": "Acme Corp",
            "organization_num_employees": 150,
            "industry": "Consulting",
            "annual_revenue": "$25M",
            "linkedin_url": "https://linkedin.com/in/jane",
        }
        fields = _extract_fields(raw)
        assert fields["email"] == "jane@acme.com"
        assert fields["title"] == "CEO"
        assert fields["company_name"] == "Acme Corp"
        assert fields["company_size"] == 150
        assert fields["industry"] == "Consulting"
        assert fields["revenue"] == "$25M"
        assert fields["linkedin_url"] == "https://linkedin.com/in/jane"

    def test_partial_response(self):
        raw = {"email": "jane@acme.com", "title": "CEO"}
        fields = _extract_fields(raw)
        assert fields["email"] == "jane@acme.com"
        assert "company_name" not in fields

    def test_empty_response(self):
        fields = _extract_fields({})
        assert len(fields) == 0

    def test_nested_organization(self):
        raw = {
            "email": "jane@acme.com",
            "company": {"name": "Acme Corp"},
        }
        fields = _extract_fields(raw)
        assert fields["company_name"] == "Acme Corp"

    def test_company_size_string_converted_to_int(self):
        raw = {"organization_num_employees": "200"}
        fields = _extract_fields(raw)
        assert fields["company_size"] == 200


# ── Waterfall Enricher ────────────────────────────────────────────────────────

class TestWaterfallEnricher:
    @pytest.mark.asyncio
    async def test_apollo_hit_enriches_record(self):
        mock_apollo = MagicMock()
        mock_apollo.get_person_detail = AsyncMock(return_value={
            "person": {
                "email": "jane@acme.com",
                "title": "CEO",
                "organization_name": "Acme Corp",
                "organization_num_employees": 150,
                "industry": "Consulting",
                "annual_revenue": "$25M",
                "linkedin_url": "https://linkedin.com/in/jane",
            }
        })

        enricher = WaterfallEnricher(apollo=mock_apollo)
        record = await enricher.enrich(
            contact_id="jane@acme.com",
            email="jane@acme.com",
            first_name="Jane",
            last_name="Doe",
        )

        assert record.waterfall_trace.apollo == WaterfallStatus.HIT
        assert record.waterfall_trace.bettercontact == WaterfallStatus.SKIPPED
        assert record.waterfall_trace.clay == WaterfallStatus.SKIPPED
        assert record.email == "jane@acme.com"
        assert record.enrichment_score == 100  # 7/7 fields
        assert record.enrichment_grade == EnrichmentGrade.READY

    @pytest.mark.asyncio
    async def test_apollo_miss_returns_low_score(self):
        mock_apollo = MagicMock()
        mock_apollo.get_person_detail = AsyncMock(return_value={"person": {}})

        enricher = WaterfallEnricher(apollo=mock_apollo)
        record = await enricher.enrich(
            contact_id="unknown@test.com",
            email="unknown@test.com",
        )

        assert record.waterfall_trace.apollo == WaterfallStatus.MISS
        assert record.enrichment_score < 70  # Only email seeded = 1/7

    @pytest.mark.asyncio
    async def test_apollo_exception_treated_as_miss(self):
        mock_apollo = MagicMock()
        mock_apollo.get_person_detail = AsyncMock(side_effect=Exception("API error"))

        enricher = WaterfallEnricher(apollo=mock_apollo)
        record = await enricher.enrich(
            contact_id="error@test.com",
            email="error@test.com",
        )

        assert record.waterfall_trace.apollo == WaterfallStatus.MISS
        assert record.enrichment_score < 100

    @pytest.mark.asyncio
    async def test_seed_fields_preserved_when_apollo_misses(self):
        mock_apollo = MagicMock()
        mock_apollo.get_person_detail = AsyncMock(return_value={"person": {}})

        enricher = WaterfallEnricher(apollo=mock_apollo)
        record = await enricher.enrich(
            contact_id="seed@test.com",
            email="seed@test.com",
            company_name="Seeded Corp",
            linkedin_url="https://linkedin.com/in/seed",
        )

        # Seeded fields should be preserved
        assert record.email == "seed@test.com"
        assert record.company_name == "Seeded Corp"
        assert record.linkedin_url == "https://linkedin.com/in/seed"

    @pytest.mark.asyncio
    async def test_null_email_after_waterfall(self):
        """If email is null after enrichment, enrichment_score reflects it."""
        mock_apollo = MagicMock()
        mock_apollo.get_person_detail = AsyncMock(return_value={
            "person": {"title": "CEO", "organization_name": "Acme"}
        })

        enricher = WaterfallEnricher(apollo=mock_apollo)
        record = await enricher.enrich(contact_id="no-email")

        assert record.email is None
        assert record.fields_filled < 7  # Missing email at minimum
