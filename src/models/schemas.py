"""Pydantic models matching output_schema.md files for all 4 agents.

All models use camelCase aliases to match the GHL-native Contact data model
and the JSON output schemas defined in the vault.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────────


class WaterfallStatus(str, Enum):
    HIT = "HIT"
    MISS = "MISS"
    SKIPPED = "SKIPPED"


class EnrichmentGrade(str, Enum):
    READY = "READY"       # 90-100
    PARTIAL = "PARTIAL"   # 70-89
    MINIMAL = "MINIMAL"   # 50-69
    REJECT = "REJECT"     # <50


class DraftApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class IcpTier(str, Enum):
    TIER_1 = "1"
    TIER_2 = "2"
    TIER_3 = "3"
    DISQUALIFIED = "DISQUALIFIED"


class Channel(str, Enum):
    INSTANTLY = "instantly"
    GHL = "ghl"
    HEYREACH = "heyreach"


# ── Recon Agent Models ─────────────────────────────────────────────────────────


class ReconRecord(BaseModel):
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field("", alias="lastName")
    title: str = ""
    company_name: str = Field("", alias="companyName")
    email: Optional[str] = None
    linkedin_url: Optional[str] = Field(None, alias="linkedinUrl")
    company_size: Optional[int] = Field(None, alias="companySize")
    industry: Optional[str] = None
    apollo_id: Optional[str] = Field(None, alias="apolloId")
    icp_tier: str = Field(..., alias="icpTier")
    base_score: int = Field(..., alias="baseScore", ge=0, le=100)
    industry_multiplier: float = Field(..., alias="industryMultiplier")
    icp_score: float = Field(..., alias="icpScore", ge=0, le=150)
    why_this_score: str = Field(..., alias="whyThisScore")
    score_breakdown: str = Field(..., alias="scoreBreakdown")

    model_config = {"populate_by_name": True}


class ReconTrace(BaseModel):
    vault_files_used: list[str] = Field(..., alias="vaultFilesUsed")
    exclusions_checked: bool = Field(True, alias="exclusionsChecked")
    disqualification_applied: bool = Field(True, alias="disqualificationApplied")
    records_found_before_filter: int = Field(..., alias="recordsFoundBeforeFilter")
    records_excluded: int = Field(..., alias="recordsExcluded")
    records_disqualified_count: int = Field(..., alias="recordsDisqualifiedCount")

    model_config = {"populate_by_name": True}


class ReconOutput(BaseModel):
    task_id: str = Field(..., alias="taskId")
    agent: str = "recon"
    timestamp: str
    records: list[ReconRecord]
    count: int
    trace: ReconTrace

    model_config = {"populate_by_name": True}


# ── Enrichment Agent Models ────────────────────────────────────────────────────


class WaterfallTrace(BaseModel):
    apollo: WaterfallStatus
    bettercontact: WaterfallStatus
    clay: WaterfallStatus


class EnrichmentRecord(BaseModel):
    contact_id: str = Field(..., alias="contactId")
    email: Optional[str] = None
    title: Optional[str] = None
    company_name: Optional[str] = Field(None, alias="companyName")
    company_size: Optional[int] = Field(None, alias="companySize")
    industry: Optional[str] = None
    revenue: Optional[str] = None
    linkedin_url: Optional[str] = Field(None, alias="linkedinUrl")
    enrichment_score: int = Field(..., alias="enrichmentScore", ge=0, le=100)
    enrichment_grade: EnrichmentGrade = Field(..., alias="enrichmentGrade")
    fields_filled: int = Field(..., alias="fieldsFilled")
    fields_total: int = Field(..., alias="fieldsTotal")
    waterfall_trace: WaterfallTrace = Field(..., alias="waterfallTrace")

    model_config = {"populate_by_name": True}


class EnrichmentTrace(BaseModel):
    vault_files_used: list[str] = Field(..., alias="vaultFilesUsed")
    records_received: int = Field(..., alias="recordsReceived")
    records_ready: int = Field(..., alias="recordsReady")
    records_partial: int = Field(..., alias="recordsPartial")
    records_minimal: int = Field(..., alias="recordsMinimal")
    records_rejected: int = Field(..., alias="recordsRejected")

    model_config = {"populate_by_name": True}


class EnrichmentOutput(BaseModel):
    task_id: str = Field(..., alias="taskId")
    agent: str = "enrichment"
    timestamp: str
    records: list[EnrichmentRecord]
    count: int
    trace: EnrichmentTrace

    model_config = {"populate_by_name": True}


# ── Segmentation Agent Models ─────────────────────────────────────────────────


class SegmentationRecord(BaseModel):
    contact_id: str = Field(..., alias="contactId")
    normalized_title: str = Field(..., alias="normalizedTitle")
    normalized_industry: str = Field(..., alias="normalizedIndustry")
    title_tier: str = Field(..., alias="titleTier")
    industry_tier: str = Field(..., alias="industryTier")
    base_score: int = Field(..., alias="baseScore", ge=0, le=100)
    industry_multiplier: float = Field(..., alias="industryMultiplier")
    icp_score: float = Field(..., alias="icpScore", ge=0, le=150)
    score_breakdown: str = Field(..., alias="scoreBreakdown")
    why_this_score: str = Field(..., alias="whyThisScore")
    icp_tier: str = Field(..., alias="icpTier")
    disqualification_reason: Optional[str] = Field(None, alias="disqualificationReason")
    rubric_citation: str = Field(..., alias="rubricCitation")

    model_config = {"populate_by_name": True}


class SegmentationTrace(BaseModel):
    vault_files_used: list[str] = Field(..., alias="vaultFilesUsed")
    records_received: int = Field(..., alias="recordsReceived")
    tier1_count: int = Field(..., alias="tier1Count")
    tier2_count: int = Field(..., alias="tier2Count")
    tier3_count: int = Field(..., alias="tier3Count")
    disqualified_count: int = Field(..., alias="disqualifiedCount")
    disqualification_applied: bool = Field(True, alias="disqualificationApplied")
    exclusions_checked: bool = Field(True, alias="exclusionsChecked")

    model_config = {"populate_by_name": True}


class SegmentationOutput(BaseModel):
    task_id: str = Field(..., alias="taskId")
    agent: str = "segmentation"
    timestamp: str
    records: list[SegmentationRecord]
    count: int
    trace: SegmentationTrace

    model_config = {"populate_by_name": True}


# ── Campaign Craft Agent Models ────────────────────────────────────────────────


class CampaignDraftTrace(BaseModel):
    lead_signals_used: list[str] = Field(..., alias="leadSignalsUsed")
    proof_points_used: list[str] = Field(..., alias="proofPointsUsed")
    cta_id: str = Field(..., alias="ctaId")

    model_config = {"populate_by_name": True}


class CampaignDraft(BaseModel):
    draft_id: str = Field(..., alias="draftId")
    contact_id: str = Field(..., alias="contactId")
    icp_tier: str = Field(..., alias="icpTier")
    angle_id: str = Field(..., alias="angleId")
    subject: str = Field(..., max_length=60)
    body: str
    channel: Channel
    booking_link: str = Field(
        "https://caio.cx/ai-exec-briefing-call",
        alias="bookingLink",
    )
    status: DraftApprovalStatus = DraftApprovalStatus.PENDING
    trace: CampaignDraftTrace

    model_config = {"populate_by_name": True}


class CampaignCraftTrace(BaseModel):
    vault_files_used: list[str] = Field(..., alias="vaultFilesUsed")
    angle_source: str = Field(..., alias="angleSource")
    signatures_applied: bool = Field(True, alias="signaturesApplied")
    compliance_checks_prepared: bool = Field(True, alias="complianceChecksPrepared")

    model_config = {"populate_by_name": True}


class CampaignCraftOutput(BaseModel):
    task_id: str = Field(..., alias="taskId")
    agent: str = "campaign-craft"
    timestamp: str
    drafts: list[CampaignDraft]
    count: int
    trace: CampaignCraftTrace

    model_config = {"populate_by_name": True}


# ── Dashboard / Storage Models ─────────────────────────────────────────────────


class StoredDraft(BaseModel):
    """A campaign draft persisted to the file-based dashboard storage."""
    draft_id: str = Field(..., alias="draftId")
    contact_id: str = Field(..., alias="contactId")
    icp_tier: str = Field(..., alias="icpTier")
    angle_id: str = Field(..., alias="angleId")
    subject: str
    body: str
    channel: Channel
    booking_link: str = Field(..., alias="bookingLink")
    status: DraftApprovalStatus = DraftApprovalStatus.PENDING
    created_at: str = Field(..., alias="createdAt")
    approved_at: Optional[str] = Field(None, alias="approvedAt")
    rejected_at: Optional[str] = Field(None, alias="rejectedAt")
    rejection_reason: Optional[str] = Field(None, alias="rejectionReason")
    ghl_push_result: Optional[dict] = Field(None, alias="ghlPushResult")

    model_config = {"populate_by_name": True}


class ValidationResult(BaseModel):
    """Result of running a validation gate."""
    gate: str
    passed: bool
    checks_run: int = Field(..., alias="checksRun")
    checks_passed: int = Field(..., alias="checksPassed")
    failures: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
