"""Unit tests for the segmentation agent — ICP scoring logic."""

import pytest

from models.schemas import EnrichmentRecord, EnrichmentGrade, WaterfallStatus, WaterfallTrace
from agents.segmentation_agent import (
    classify_title,
    classify_industry,
    score_company_size,
    score_revenue,
    check_disqualification,
    score_contact,
    segment_batch,
)
from utils.vault_loader import load_tier_definitions, Exclusions


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def tiers():
    return load_tier_definitions()


@pytest.fixture
def empty_exclusions():
    return Exclusions(blocked_domains=set(), blocked_emails=set())


def _make_enrichment_record(**overrides) -> EnrichmentRecord:
    defaults = dict(
        contactId="test@example.com",
        email="test@example.com",
        title="CEO",
        companyName="Acme Corp",
        companySize=150,
        industry="consulting",
        revenue="$25M",
        linkedinUrl="https://linkedin.com/in/test",
        enrichmentScore=86,
        enrichmentGrade=EnrichmentGrade.PARTIAL,
        fieldsFilled=6,
        fieldsTotal=7,
        waterfallTrace=WaterfallTrace(
            apollo=WaterfallStatus.HIT,
            bettercontact=WaterfallStatus.SKIPPED,
            clay=WaterfallStatus.SKIPPED,
        ),
    )
    defaults.update(overrides)
    return EnrichmentRecord(**defaults)


# ── Title Classification ──────────────────────────────────────────────────────

class TestClassifyTitle:
    def test_ceo_is_tier1(self, tiers):
        assert classify_title("CEO", tiers) == "tier_1"

    def test_founder_is_tier1(self, tiers):
        assert classify_title("Founder & President", tiers) == "tier_1"

    def test_cto_is_tier2(self, tiers):
        assert classify_title("CTO", tiers) == "tier_2"

    def test_vp_operations_is_tier2(self, tiers):
        assert classify_title("VP of Operations", tiers) == "tier_2"

    def test_head_of_data_is_tier3(self, tiers):
        assert classify_title("Head of Data", tiers) == "tier_3"

    def test_head_of_ai_is_tier3(self, tiers):
        assert classify_title("Head of AI", tiers) == "tier_3"

    def test_operations_manager(self, tiers):
        assert classify_title("Operations Manager", tiers) == "manager"

    def test_generic_manager(self, tiers):
        assert classify_title("Regional Manager", tiers) == "manager"

    def test_unmatched_title(self, tiers):
        assert classify_title("Intern", tiers) == "unmatched"

    def test_case_insensitive(self, tiers):
        assert classify_title("ceo", tiers) == "tier_1"
        assert classify_title("FOUNDER", tiers) == "tier_1"


# ── Industry Classification ───────────────────────────────────────────────────

class TestClassifyIndustry:
    def test_consulting_is_tier1(self, tiers):
        assert classify_industry("consulting", tiers) == "tier_1"

    def test_agencies_is_tier1(self, tiers):
        assert classify_industry("Digital Agencies", tiers) == "tier_1"

    def test_saas_is_tier2(self, tiers):
        assert classify_industry("B2B SaaS", tiers) == "tier_2"

    def test_healthcare_is_tier2(self, tiers):
        assert classify_industry("Healthcare", tiers) == "tier_2"

    def test_manufacturing_is_tier3(self, tiers):
        assert classify_industry("Manufacturing", tiers) == "tier_3"

    def test_unmatched_industry(self, tiers):
        assert classify_industry("Cryptocurrency", tiers) == "unmatched"


# ── Company Size Scoring ──────────────────────────────────────────────────────

class TestScoreCompanySize:
    def test_sweet_spot_101_250(self):
        assert score_company_size(150) == 20

    def test_51_100(self):
        assert score_company_size(75) == 15

    def test_251_500(self):
        assert score_company_size(300) == 15

    def test_10_50(self):
        assert score_company_size(25) == 10

    def test_501_1000(self):
        assert score_company_size(750) == 10

    def test_too_small(self):
        assert score_company_size(5) == 0

    def test_too_large(self):
        assert score_company_size(5000) == 0

    def test_none(self):
        assert score_company_size(None) == 0


# ── Revenue Scoring ───────────────────────────────────────────────────────────

class TestScoreRevenue:
    def test_sweet_spot_10m_50m(self):
        assert score_revenue("$25M") == 15

    def test_5m_10m(self):
        assert score_revenue("$7M") == 12

    def test_50m_100m(self):
        assert score_revenue("$75M") == 12

    def test_1m_5m(self):
        assert score_revenue("$3M") == 8

    def test_gt_100m(self):
        assert score_revenue("$500M") == 8

    def test_lt_1m(self):
        assert score_revenue("$500K") == 0

    def test_none(self):
        assert score_revenue(None) == 0

    def test_unparseable(self):
        assert score_revenue("unknown") == 0


# ── Disqualification Checks ──────────────────────────────────────────────────

class TestDisqualification:
    def test_too_small(self, empty_exclusions):
        record = _make_enrichment_record(companySize=5)
        result = check_disqualification(record, empty_exclusions)
        assert result is not None
        assert result[0] == "DQ-001"

    def test_too_large(self, empty_exclusions):
        record = _make_enrichment_record(companySize=5000)
        result = check_disqualification(record, empty_exclusions)
        assert result is not None
        assert result[0] == "DQ-002"

    def test_government(self, empty_exclusions):
        record = _make_enrichment_record(industry="Government")
        result = check_disqualification(record, empty_exclusions)
        assert result is not None
        assert result[0] == "DQ-003"

    def test_nonprofit(self, empty_exclusions):
        record = _make_enrichment_record(industry="Non-profit")
        result = check_disqualification(record, empty_exclusions)
        assert result is not None
        assert result[0] == "DQ-004"

    def test_education(self, empty_exclusions):
        record = _make_enrichment_record(industry="Education")
        result = check_disqualification(record, empty_exclusions)
        assert result is not None
        assert result[0] == "DQ-005"

    def test_current_customer(self, empty_exclusions):
        record = _make_enrichment_record()
        result = check_disqualification(record, empty_exclusions, tags=["Customer"])
        assert result is not None
        assert result[0] == "DQ-006"

    def test_blocked_domain(self):
        exc = Exclusions(blocked_domains={"blocked.com"}, blocked_emails=set())
        record = _make_enrichment_record(email="user@blocked.com", contactId="user@blocked.com")
        result = check_disqualification(record, exc)
        assert result is not None
        assert "DQ-008" in result[0]

    def test_blocked_email(self):
        exc = Exclusions(blocked_domains=set(), blocked_emails={"bad@example.com"})
        record = _make_enrichment_record(email="bad@example.com", contactId="bad@example.com")
        result = check_disqualification(record, exc)
        assert result is not None

    def test_clean_record_passes(self, empty_exclusions):
        record = _make_enrichment_record()
        result = check_disqualification(record, empty_exclusions)
        assert result is None


# ── Full Scoring Pipeline ─────────────────────────────────────────────────────

class TestScoreContact:
    def test_ceo_consulting_150emp_25m_is_tier1(self, tiers, empty_exclusions):
        """Worked example from PRD: CEO consulting 150emp $25M → Tier 1."""
        record = _make_enrichment_record(
            title="CEO", industry="consulting", companySize=150, revenue="$25M"
        )
        result = score_contact(record, tiers, empty_exclusions)
        # Size=20 + Title=25 + Industry=20 + Revenue=15 = 80, mult=1.5, score=120.0
        assert result.base_score == 80
        assert result.industry_multiplier == 1.5
        assert result.icp_score == 120.0
        assert result.icp_tier == "1"

    def test_operations_manager_manufacturing_small(self, tiers, empty_exclusions):
        """Lower-scoring profile → should be Tier 3 or DQ."""
        record = _make_enrichment_record(
            title="Operations Manager",
            industry="Manufacturing",
            companySize=30,
            revenue="$2M",
        )
        result = score_contact(record, tiers, empty_exclusions)
        # Size=10, Title=12, Industry=10, Revenue=8 = 40, mult=1.0, score=40.0
        assert result.icp_tier == "3"

    def test_disqualified_record_gets_zero_score(self, tiers, empty_exclusions):
        record = _make_enrichment_record(industry="Government", companySize=150)
        result = score_contact(record, tiers, empty_exclusions)
        assert result.icp_tier == "DISQUALIFIED"
        assert result.base_score == 0

    def test_tier_boundary_80_is_tier1(self, tiers, empty_exclusions):
        """Score exactly 80.0 should be Tier 1."""
        # CEO (25) + consulting (20) + 101-250 (20) + 10m-50m (15) = 80, mult=1.5 → 120 → T1
        record = _make_enrichment_record(
            title="CEO", industry="consulting", companySize=150, revenue="$25M"
        )
        result = score_contact(record, tiers, empty_exclusions)
        assert result.icp_score >= 80.0
        assert result.icp_tier == "1"

    def test_tier_boundary_below_40_is_dq(self, tiers, empty_exclusions):
        """Score below 40 should be DISQUALIFIED."""
        record = _make_enrichment_record(
            title="Intern",
            industry="Cryptocurrency",
            companySize=5000,
            revenue=None,
        )
        result = score_contact(record, tiers, empty_exclusions)
        assert result.icp_score < 40.0
        assert result.icp_tier == "DISQUALIFIED"


# ── Batch Segmentation ────────────────────────────────────────────────────────

class TestSegmentBatch:
    def test_batch_counts_match(self, tiers, empty_exclusions):
        records = [
            _make_enrichment_record(contactId="a@test.com", title="CEO", industry="consulting"),
            _make_enrichment_record(contactId="b@test.com", title="Intern", industry="Crypto", companySize=5000),
        ]
        output = segment_batch("TASK-001", records, tiers, empty_exclusions)
        assert output.count == 2
        assert len(output.records) == 2
        assert output.trace.records_received == 2

    def test_batch_tier_distribution(self, tiers, empty_exclusions):
        records = [
            _make_enrichment_record(contactId="ceo@test.com", title="CEO", industry="consulting", companySize=150, revenue="$25M"),
            _make_enrichment_record(contactId="intern@test.com", title="Intern", industry="unknown", companySize=5000, revenue=None),
        ]
        output = segment_batch("TASK-002", records, tiers, empty_exclusions)
        assert output.trace.tier1_count >= 1
        assert output.trace.disqualified_count >= 1
