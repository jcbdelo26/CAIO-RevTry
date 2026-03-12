"""Unit tests for gate validators (Gates 1-3)."""

import pytest
from datetime import datetime, timezone

from models.schemas import (
    CampaignCraftOutput,
    CampaignCraftTrace,
    CampaignDraft,
    CampaignDraftTrace,
    Channel,
    DraftApprovalStatus,
    EnrichmentGrade,
    EnrichmentOutput,
    EnrichmentRecord,
    EnrichmentTrace,
    SegmentationOutput,
    SegmentationRecord,
    SegmentationTrace,
    WaterfallStatus,
    WaterfallTrace,
)
from validators.gate1_validator import validate_gate1
from validators.gate2_validator import validate_gate2
from validators.gate3_validator import validate_gate3
from utils.vault_loader import Exclusions, load_email_angles, load_signatures


# ── Helpers ────────────────────────────────────────────────────────────────────

BOOKING_LINK = "https://caio.cx/ai-exec-briefing-call"


def _make_draft(**overrides) -> CampaignDraft:
    defaults = dict(
        draftId="abc123",
        contactId="test@example.com",
        icpTier="1",
        angleId="ai_executive_briefing",
        subject="AI strategy for consulting",
        body=(
            "Hi Test,\n\n"
            "As a leader in the consulting space, you're likely seeing AI reshape how teams operate.\n\n"
            "We've helped similar companies streamline operations and unlock measurable results.\n\n"
            f"Book a time here: {BOOKING_LINK}\n\n"
            "Dani Apgar\n"
            "Head of Sales, Chief AI Officer\n\n"
            "Reply STOP to unsubscribe.\n"
            "Chief AI Officer LLC | 2021 Guadalupe Street, Suite 260, Austin, Texas 78705"
        ),
        channel=Channel.GHL,
        bookingLink=BOOKING_LINK,
        status=DraftApprovalStatus.PENDING,
        trace=CampaignDraftTrace(
            leadSignalsUsed=["consulting", "ceo"],
            proofPointsUsed=[],
            ctaId="exec_briefing",
        ),
    )
    defaults.update(overrides)
    return CampaignDraft(**defaults)


def _make_campaign_output(drafts=None) -> CampaignCraftOutput:
    if drafts is None:
        drafts = [_make_draft()]
    return CampaignCraftOutput(
        taskId="TASK-001",
        agent="campaign-craft",
        timestamp=datetime.now(timezone.utc).isoformat(),
        drafts=drafts,
        count=len(drafts),
        trace=CampaignCraftTrace(
            vaultFilesUsed=["vault/playbook/email_angles.md"],
            angleSource="vault/playbook/email_angles.md",
            signaturesApplied=True,
            complianceChecksPrepared=True,
        ),
    )


def _make_segmentation_output() -> SegmentationOutput:
    return SegmentationOutput(
        taskId="TASK-001",
        agent="segmentation",
        timestamp=datetime.now(timezone.utc).isoformat(),
        records=[
            SegmentationRecord(
                contactId="test@example.com",
                normalizedTitle="ceo",
                normalizedIndustry="consulting",
                titleTier="tier_1",
                industryTier="tier_1",
                baseScore=80,
                industryMultiplier=1.5,
                icpScore=120.0,
                scoreBreakdown="Size:20 Title:25 Industry:20 Revenue:15",
                whyThisScore="Full score breakdown",
                icpTier="1",
                rubricCitation="scoring_rules.md",
            )
        ],
        count=1,
        trace=SegmentationTrace(
            vaultFilesUsed=["vault/icp/scoring_rules.md"],
            recordsReceived=1,
            tier1Count=1,
            tier2Count=0,
            tier3Count=0,
            disqualifiedCount=0,
        ),
    )


# ── Gate 1 Tests ──────────────────────────────────────────────────────────────

class TestGate1:
    def test_valid_campaign_output_passes(self):
        output = _make_campaign_output()
        result = validate_gate1(output)
        assert result.passed is True
        assert result.checks_run == 6
        assert result.checks_passed == 6

    def test_mismatched_count_fails(self):
        output = _make_campaign_output()
        output.count = 999  # Wrong count
        result = validate_gate1(output)
        assert result.passed is False
        assert any("count" in f.lower() for f in result.failures)

    def test_empty_task_id_fails(self):
        output = _make_campaign_output()
        output.task_id = ""
        result = validate_gate1(output)
        assert result.passed is False
        assert any("required fields" in f.lower() for f in result.failures)

    def test_placeholder_in_body_fails(self):
        draft = _make_draft(body="This is a TBD placeholder body")
        output = _make_campaign_output(drafts=[draft])
        result = validate_gate1(output)
        assert result.passed is False
        assert any("placeholder" in f.lower() for f in result.failures)


# ── Gate 2 Tests ──────────────────────────────────────────────────────────────

class TestGate2:
    @pytest.fixture
    def exclusions(self):
        return Exclusions(
            blocked_domains={"blocked.com"},
            blocked_emails={"spammer@evil.com"},
        )

    @pytest.fixture
    def signatures(self):
        return load_signatures()

    def test_compliant_draft_passes(self, exclusions, signatures):
        output = _make_campaign_output()
        result = validate_gate2(output, exclusions, signatures)
        assert result.passed is True

    def test_blocked_domain_fails(self, exclusions, signatures):
        draft = _make_draft(contactId="user@blocked.com")
        output = _make_campaign_output(drafts=[draft])
        result = validate_gate2(output, exclusions, signatures)
        assert result.passed is False
        assert any("blocked domain" in f.lower() for f in result.failures)

    def test_blocked_email_fails(self, exclusions, signatures):
        draft = _make_draft(contactId="spammer@evil.com")
        output = _make_campaign_output(drafts=[draft])
        result = validate_gate2(output, exclusions, signatures)
        assert result.passed is False

    def test_missing_can_spam_footer_fails(self, exclusions, signatures):
        draft = _make_draft(body="Hi there,\n\nJust a quick note.\n\nDani Apgar")
        output = _make_campaign_output(drafts=[draft])
        result = validate_gate2(output, exclusions, signatures)
        assert result.passed is False
        assert any("CAN-SPAM" in f for f in result.failures)

    def test_spam_trigger_in_subject_fails(self, exclusions, signatures):
        draft = _make_draft(subject="Free AI consultation guaranteed")
        output = _make_campaign_output(drafts=[draft])
        result = validate_gate2(output, exclusions, signatures)
        assert result.passed is False

    def test_all_caps_subject_fails(self, exclusions, signatures):
        draft = _make_draft(subject="AMAZING OFFER for your company")
        output = _make_campaign_output(drafts=[draft])
        result = validate_gate2(output, exclusions, signatures)
        assert result.passed is False

    def test_allowed_acronyms_pass(self, exclusions, signatures):
        """AI, CRM, SaaS etc. should not trigger ALL-CAPS check."""
        draft = _make_draft(subject="AI strategy for your CRM")
        output = _make_campaign_output(drafts=[draft])
        result = validate_gate2(output, exclusions, signatures)
        assert result.passed is True

    def test_banned_opener_fails(self, exclusions, signatures):
        draft = _make_draft(
            body=(
                "Hope this finds you well!\n\n"
                f"Book a time here: {BOOKING_LINK}\n\n"
                "Dani Apgar\nHead of Sales, Chief AI Officer\n\n"
                "Reply STOP to unsubscribe.\n"
                "Chief AI Officer LLC | 2021 Guadalupe Street, Suite 260, Austin, Texas 78705"
            )
        )
        output = _make_campaign_output(drafts=[draft])
        result = validate_gate2(output, exclusions, signatures)
        assert result.passed is False
        assert any("banned opener" in f.lower() for f in result.failures)

    def test_deferred_channel_fails(self, exclusions, signatures):
        """Instantly/HeyReach channels should fail Gate 2 — only GHL active."""
        draft = _make_draft(channel=Channel.INSTANTLY)
        output = _make_campaign_output(drafts=[draft])
        result = validate_gate2(output, exclusions, signatures)
        assert result.passed is False
        assert any("deferred channel" in f.lower() for f in result.failures)

    def test_ghl_channel_passes(self, exclusions, signatures):
        """GHL channel should pass the channel routing check."""
        draft = _make_draft(channel=Channel.GHL)
        output = _make_campaign_output(drafts=[draft])
        result = validate_gate2(output, exclusions, signatures)
        assert result.passed is True

    def test_batch_over_200_fails(self, exclusions, signatures):
        drafts = [_make_draft(draftId=f"draft-{i}", contactId=f"u{i}@test.com") for i in range(201)]
        output = _make_campaign_output(drafts=drafts)
        output.count = 201
        result = validate_gate2(output, exclusions, signatures)
        assert result.passed is False
        assert any("rate limit" in f.lower() for f in result.failures)


# ── Gate 3 Tests ──────────────────────────────────────────────────────────────

class TestGate3:
    def test_valid_output_passes(self):
        output = _make_campaign_output()
        seg = _make_segmentation_output()
        angles = load_email_angles()
        signatures = load_signatures()
        result = validate_gate3(output, seg, angles, signatures)
        assert result.passed is True
        assert result.checks_run == 7

    def test_wrong_angle_for_tier_fails(self):
        # quick_win is NOT allowed for Tier 1
        draft = _make_draft(icpTier="1", angleId="quick_win")
        output = _make_campaign_output(drafts=[draft])
        angles = load_email_angles()
        signatures = load_signatures()
        result = validate_gate3(output, None, angles, signatures)
        assert result.passed is False
        assert any("angle" in f.lower() for f in result.failures)

    def test_wrong_booking_link_fails(self):
        draft = _make_draft(bookingLink="https://wrong.com/link")
        output = _make_campaign_output(drafts=[draft])
        angles = load_email_angles()
        signatures = load_signatures()
        result = validate_gate3(output, None, angles, signatures)
        assert result.passed is False
        assert any("booking link" in f.lower() for f in result.failures)

    def test_missing_sender_name_fails(self):
        draft = _make_draft(
            body=(
                f"Hi there,\n\nGreat opportunity.\n\n{BOOKING_LINK}\n\n"
                "Reply STOP to unsubscribe.\n"
                "Chief AI Officer LLC | 2021 Guadalupe Street, Suite 260, Austin, Texas 78705"
            )
        )
        output = _make_campaign_output(drafts=[draft])
        angles = load_email_angles()
        signatures = load_signatures()
        result = validate_gate3(output, None, angles, signatures)
        assert result.passed is False
        assert any("sender" in f.lower() for f in result.failures)
