"""Unit tests for quality guards (GUARD-001 through GUARD-005)."""

import pytest

from models.schemas import (
    CampaignDraft,
    CampaignDraftTrace,
    Channel,
    DraftApprovalStatus,
    EnrichmentGrade,
    EnrichmentRecord,
    WaterfallStatus,
    WaterfallTrace,
)
from validators.guards import (
    guard_001_rejection_check,
    guard_002_duplicate_check,
    guard_003_enrichment_check,
    guard_004_banned_opener_check,
    guard_005_generic_density_check,
    compute_draft_hash,
    run_all_guards,
)
from utils.vault_loader import load_signatures

BOOKING_LINK = "https://caio.cx/ai-exec-briefing-call"


def _make_draft(**overrides) -> CampaignDraft:
    defaults = dict(
        draftId="test-draft-001",
        contactId="test@example.com",
        icpTier="1",
        angleId="ai_executive_briefing",
        subject="AI strategy for consulting",
        body=(
            "Hi Test,\n\n"
            "As a leader in the consulting space.\n\n"
            f"Book a time here: {BOOKING_LINK}\n\n"
            "Dani Apgar\nHead of Sales, Chief AI Officer\n\n"
            "Reply STOP to unsubscribe.\n"
            "Chief AI Officer LLC | 2021 Guadalupe Street, Suite 260, Austin, Texas 78705"
        ),
        channel=Channel.INSTANTLY,
        bookingLink=BOOKING_LINK,
        status=DraftApprovalStatus.PENDING,
        trace=CampaignDraftTrace(
            leadSignalsUsed=["consulting"],
            proofPointsUsed=[],
            ctaId="exec_briefing",
        ),
    )
    defaults.update(overrides)
    return CampaignDraft(**defaults)


def _make_enrichment_record(**overrides) -> EnrichmentRecord:
    defaults = dict(
        contactId="test@example.com",
        email="test@example.com",
        title="CEO",
        companyName="Acme",
        companySize=150,
        industry="consulting",
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


# ── GUARD-001: Rejection Frequency ────────────────────────────────────────────

class TestGuard001:
    def test_no_feedback_dir_passes(self, tmp_path):
        blocked, reason = guard_001_rejection_check(
            "test@example.com",
            feedback_dir=str(tmp_path / "nonexistent"),
        )
        assert blocked is False
        assert reason is None

    def test_no_rejections_passes(self, tmp_path):
        feedback_dir = tmp_path / "registry"
        pending = feedback_dir / "pending_feedback"
        pending.mkdir(parents=True)
        blocked, reason = guard_001_rejection_check(
            "test@example.com",
            feedback_dir=str(feedback_dir),
        )
        assert blocked is False

    def test_two_rejections_blocks(self, tmp_path):
        feedback_dir = tmp_path / "registry"
        pending = feedback_dir / "pending_feedback"
        pending.mkdir(parents=True)
        # Create 2 rejection files
        for i in range(2):
            (pending / f"reject-{i}.md").write_text(
                f"contact: test@example.com\nstatus: REJECTED\nreason: bad draft {i}"
            )
        blocked, reason = guard_001_rejection_check(
            "test@example.com",
            feedback_dir=str(feedback_dir),
        )
        assert blocked is True
        assert "GUARD-001" in reason

    def test_old_rejections_outside_window_pass(self, tmp_path):
        """Rejections older than window_days should not count."""
        import os
        import time

        feedback_dir = tmp_path / "registry"
        pending = feedback_dir / "pending_feedback"
        pending.mkdir(parents=True)
        # Create 2 rejection files with old modification times (60 days ago)
        old_time = time.time() - (60 * 86400)
        for i in range(2):
            f = pending / f"reject-old-{i}.md"
            f.write_text(
                f"contact: test@example.com\nstatus: REJECTED\nreason: old {i}"
            )
            os.utime(str(f), (old_time, old_time))
        blocked, reason = guard_001_rejection_check(
            "test@example.com",
            feedback_dir=str(feedback_dir),
            window_days=30,
        )
        assert blocked is False
        assert reason is None


# ── GUARD-002: Duplicate Hash ─────────────────────────────────────────────────

class TestGuard002:
    def test_no_duplicates_passes(self):
        draft = _make_draft()
        blocked, reason = guard_002_duplicate_check(draft, sent_hashes=set())
        assert blocked is False

    def test_duplicate_hash_blocks(self):
        draft = _make_draft()
        hash_val = compute_draft_hash(draft)
        blocked, reason = guard_002_duplicate_check(draft, sent_hashes={hash_val})
        assert blocked is True
        assert "GUARD-002" in reason

    def test_none_hashes_passes(self):
        draft = _make_draft()
        blocked, reason = guard_002_duplicate_check(draft, sent_hashes=None)
        assert blocked is False


# ── GUARD-003: Enrichment Score Threshold ─────────────────────────────────────

class TestGuard003:
    def test_score_above_threshold_passes(self):
        record = _make_enrichment_record(enrichmentScore=85)
        blocked, reason = guard_003_enrichment_check(record)
        assert blocked is False

    def test_score_at_threshold_passes(self):
        """Boundary: exactly 70 should pass."""
        record = _make_enrichment_record(enrichmentScore=70)
        blocked, reason = guard_003_enrichment_check(record)
        assert blocked is False

    def test_score_below_threshold_blocks(self):
        """Boundary: 69 should block."""
        record = _make_enrichment_record(enrichmentScore=69)
        blocked, reason = guard_003_enrichment_check(record)
        assert blocked is True
        assert "GUARD-003" in reason

    def test_custom_threshold(self):
        record = _make_enrichment_record(enrichmentScore=50)
        blocked, _ = guard_003_enrichment_check(record, threshold=50)
        assert blocked is False


# ── GUARD-004: Banned Openers ─────────────────────────────────────────────────

class TestGuard004:
    def test_clean_opener_passes(self):
        draft = _make_draft()
        signatures = load_signatures()
        blocked, reason = guard_004_banned_opener_check(draft, signatures)
        assert blocked is False

    def test_banned_opener_blocks(self):
        draft = _make_draft(body="Hope this finds you well!\n\nRest of email...")
        signatures = load_signatures()
        blocked, reason = guard_004_banned_opener_check(draft, signatures)
        assert blocked is True
        assert "GUARD-004" in reason

    def test_case_insensitive_banned_opener(self):
        draft = _make_draft(body="HOPE THIS FINDS YOU WELL!\n\nRest...")
        signatures = load_signatures()
        blocked, reason = guard_004_banned_opener_check(draft, signatures)
        assert blocked is True


# ── GUARD-005: Generic Density ────────────────────────────────────────────────

class TestGuard005:
    def test_clean_body_passes(self):
        draft = _make_draft()
        blocked, reason = guard_005_generic_density_check(draft)
        assert blocked is False

    def test_too_many_generic_phrases_blocks(self):
        draft = _make_draft(
            body=(
                "In today's rapidly evolving landscape, our cutting-edge "
                "solution leverages synergy and paradigm shift thinking. "
                "This is a game-changer and revolutionary approach."
            )
        )
        blocked, reason = guard_005_generic_density_check(draft)
        assert blocked is True
        assert "GUARD-005" in reason

    def test_exactly_at_threshold_blocks(self):
        """3 generic phrases = threshold, should block."""
        draft = _make_draft(
            body="In today's rapidly evolving cutting-edge world, we help."
        )
        blocked, reason = guard_005_generic_density_check(draft, threshold=3)
        assert blocked is True

    def test_below_threshold_passes(self):
        draft = _make_draft(body="In today's market, we offer leverage for growth.")
        blocked, reason = guard_005_generic_density_check(draft, threshold=3)
        assert blocked is False


# ── Run All Guards ────────────────────────────────────────────────────────────

class TestRunAllGuards:
    def test_clean_draft_no_failures(self):
        draft = _make_draft()
        record = _make_enrichment_record(enrichmentScore=85)
        signatures = load_signatures()
        failures = run_all_guards(draft, record, sent_hashes=set(), signatures=signatures)
        assert len(failures) == 0

    def test_multiple_guard_failures(self):
        draft = _make_draft(
            body="Hope this finds you well! In today's rapidly evolving cutting-edge leverage synergy paradigm shift world."
        )
        record = _make_enrichment_record(enrichmentScore=50)
        signatures = load_signatures()
        failures = run_all_guards(draft, record, signatures=signatures)
        guard_ids = [f[0] for f in failures]
        assert "GUARD-003" in guard_ids
        assert "GUARD-004" in guard_ids
        assert "GUARD-005" in guard_ids
