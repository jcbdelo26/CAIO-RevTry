"""Segmentation Agent — Authoritative ICP scoring.

Pure logic, no API calls. Takes enriched records and produces
authoritative ICP scores using scoring_rules.md and tier_definitions.md.

Mandatory calculation order:
1. Check exclusions (DQ-008/009 first)
2. Check DQ rules (DQ-001 through DQ-007)
3. base_score = sum of 6 components
4. multiplier = highest of title tier or industry tier
5. icp_score = round(base_score * multiplier, 1)
6. Tier: >=80=T1, 60-79.9=T2, 40-59.9=T3, <40=DQ
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from models.schemas import (
    EnrichmentRecord,
    SegmentationOutput,
    SegmentationRecord,
    SegmentationTrace,
)
from utils.exclusion_checker import ExclusionResult, check_exclusions
from utils.vault_loader import (
    Exclusions,
    TierDefinitions,
    load_exclusions,
    load_scoring_rules,
    load_tier_definitions,
    load_disqualification_rules,
)


# ── Title Matching ─────────────────────────────────────────────────────────────


def _normalize_title(title: str) -> str:
    """Lowercase, strip punctuation, normalize whitespace."""
    t = title.lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def classify_title(title: str, tiers: TierDefinitions) -> str:
    """Return tier key: 'tier_1', 'tier_2', 'tier_3', 'manager', or 'unmatched'."""
    normalized = _normalize_title(title)

    # Check tiers in order (Tier 1 first)
    for tier_key in ["tier_1", "tier_2", "tier_3"]:
        for keyword in tiers.title_buckets[tier_key]:
            # Match keyword as substring (handles "VP of Operations" matching "vp operations")
            kw_normalized = keyword.lower().replace(" of ", " ").replace(" ", " ")
            # Remove common filler words for matching
            title_cleaned = normalized.replace(" of ", " ").replace(" the ", " ")
            if kw_normalized in title_cleaned or title_cleaned.startswith(kw_normalized):
                return tier_key

    # Check manager
    for keyword in tiers.title_buckets["manager"]:
        if keyword.lower() in normalized:
            return "manager"

    # Fallback: check if "manager" appears anywhere
    if "manager" in normalized:
        return "manager"

    return "unmatched"


# ── Industry Matching ──────────────────────────────────────────────────────────


def _normalize_industry(industry: str) -> str:
    return industry.lower().strip()


def classify_industry(industry: str, tiers: TierDefinitions) -> str:
    """Return tier key: 'tier_1', 'tier_2', 'tier_3', or 'unmatched'."""
    normalized = _normalize_industry(industry)

    for tier_key in ["tier_1", "tier_2", "tier_3"]:
        for keyword in tiers.industry_tiers[tier_key]:
            if keyword.lower() in normalized or normalized in keyword.lower():
                return tier_key

    return "unmatched"


# ── Company Size Scoring ──────────────────────────────────────────────────────


def score_company_size(size: Optional[int]) -> int:
    if size is None:
        return 0
    if 101 <= size <= 250:
        return 20
    elif 51 <= size <= 100:
        return 15
    elif 251 <= size <= 500:
        return 15
    elif 10 <= size <= 50:
        return 10
    elif 501 <= size <= 1000:
        return 10
    return 0


# ── Revenue Scoring ───────────────────────────────────────────────────────────


def _parse_revenue(revenue: Optional[str]) -> Optional[float]:
    """Parse revenue string to millions. Returns None if unparseable."""
    if not revenue:
        return None
    rev_str = revenue.lower().replace("$", "").replace(",", "").strip()
    try:
        if "b" in rev_str:
            return float(re.sub(r"[^\d.]", "", rev_str)) * 1000
        elif "m" in rev_str:
            return float(re.sub(r"[^\d.]", "", rev_str))
        elif "k" in rev_str:
            return float(re.sub(r"[^\d.]", "", rev_str)) / 1000
        else:
            val = float(rev_str)
            if val > 10000:  # likely in raw dollars
                return val / 1_000_000
            return val
    except (ValueError, TypeError):
        return None


def score_revenue(revenue: Optional[str]) -> int:
    millions = _parse_revenue(revenue)
    if millions is None:
        return 0
    if 10 <= millions <= 50:
        return 15
    elif 5 <= millions < 10:
        return 12
    elif 50 < millions <= 100:
        return 12
    elif 1 <= millions < 5:
        return 8
    elif millions > 100:
        return 8
    return 0  # <$1M


# ── Disqualification Checks ───────────────────────────────────────────────────


DQ_INDUSTRIES = {
    "government": "DQ-003",
    "non-profit": "DQ-004",
    "nonprofit": "DQ-004",
    "education": "DQ-005",
    "academia": "DQ-005",
}


def check_disqualification(
    record: EnrichmentRecord,
    exclusions: Exclusions,
    tags: Optional[list[str]] = None,
) -> Optional[tuple[str, str]]:
    """Check DQ rules in evaluation order. Returns (rule_id, reason) or None."""

    # DQ-008/009: Exclusions (fastest lookup first)
    if record.email:
        exc_result = check_exclusions(record.email, exclusions)
        if exc_result.is_blocked:
            return (exc_result.rule_id or "DQ-008", exc_result.reason or "Blocked by exclusions")

    # DQ-006: Current customer (tag check)
    if tags and any(t.lower() == "customer" for t in tags):
        return ("DQ-006", "Contact is a current customer (has 'Customer' tag)")

    # DQ-007: Competitor (would require competitor domain list - skip for now)

    # DQ-003/004/005: Industry check
    if record.industry:
        industry_lower = record.industry.lower().strip()
        for industry_kw, rule_id in DQ_INDUSTRIES.items():
            if industry_kw in industry_lower:
                rule_names = {"DQ-003": "Government", "DQ-004": "Non-profit", "DQ-005": "Education"}
                return (rule_id, f"{rule_id}: Industry is {rule_names[rule_id]} ('{record.industry}')")

    # DQ-001: Too small
    if record.company_size is not None and record.company_size < 10:
        return ("DQ-001", f"DQ-001: Company has {record.company_size} employees (<10 limit)")

    # DQ-002: Too large
    if record.company_size is not None and record.company_size > 1000:
        return ("DQ-002", f"DQ-002: Company has {record.company_size} employees (>1,000 limit)")

    return None


# ── Main Scoring Function ─────────────────────────────────────────────────────


def score_contact(
    record: EnrichmentRecord,
    tiers: TierDefinitions,
    exclusions: Exclusions,
    tags: Optional[list[str]] = None,
    tech_signal: str = "no_signal",
    engagement_signal: str = "none",
) -> SegmentationRecord:
    """Score a single enriched contact. Returns a SegmentationRecord."""

    # Step 1+2: Check disqualification
    dq = check_disqualification(record, exclusions, tags)
    if dq is not None:
        rule_id, reason = dq
        return SegmentationRecord(
            contactId=record.contact_id,
            normalizedTitle=_normalize_title(record.title or ""),
            normalizedIndustry=_normalize_industry(record.industry or ""),
            titleTier="unmatched",
            industryTier="unmatched",
            baseScore=0,
            industryMultiplier=0.0,
            icpScore=0.0,
            scoreBreakdown=f"DISQUALIFIED by {rule_id}",
            whyThisScore=reason,
            icpTier="DISQUALIFIED",
            disqualificationReason=reason,
            rubricCitation=f"disqualification.md rule {rule_id}",
        )

    # Step 3: Calculate base_score
    title_tier = classify_title(record.title or "", tiers)
    industry_tier = classify_industry(record.industry or "", tiers)

    size_score = score_company_size(record.company_size)
    title_score = tiers.title_points.get(title_tier, 0)
    industry_score = tiers.industry_points.get(industry_tier, 0)
    rev_score = score_revenue(record.revenue)

    tech_scores = {"active_ai_hiring": 10, "ai_tools_adopted": 7, "no_signal": 0}
    tech_score = tech_scores.get(tech_signal, 0)

    engagement_scores = {"website_visit": 10, "content_download": 7, "social_engagement": 5, "none": 0}
    eng_score = engagement_scores.get(engagement_signal, 0)

    base_score = size_score + title_score + industry_score + rev_score + tech_score + eng_score

    # Step 4: Multiplier = highest of title tier or industry tier
    title_mult = tiers.industry_multipliers.get(title_tier, 0.8)
    industry_mult = tiers.industry_multipliers.get(industry_tier, 0.8)
    multiplier = max(title_mult, industry_mult)

    # Step 5: icp_score
    icp_score = round(base_score * multiplier, 1)

    # Step 6: Tier assignment
    if icp_score >= 80.0:
        icp_tier = "1"
    elif icp_score >= 60.0:
        icp_tier = "2"
    elif icp_score >= 40.0:
        icp_tier = "3"
    else:
        icp_tier = "DISQUALIFIED"

    # Build breakdown string
    breakdown = (
        f"Size: {size_score} ({record.company_size or 'unknown'} employees), "
        f"Title: {title_score} ({record.title or 'unknown'} = {title_tier}), "
        f"Industry: {industry_score} ({record.industry or 'unknown'} = {industry_tier}), "
        f"Revenue: {rev_score} ({record.revenue or 'unknown'}), "
        f"Tech: {tech_score} ({tech_signal}), "
        f"Engagement: {eng_score} ({engagement_signal}) "
        f"→ base={base_score}, mult={multiplier}, icp_score={icp_score}"
    )

    why = (
        f"Size: {size_score} ({record.company_size or 'unknown'} employees), "
        f"Title: {title_score} ({title_tier}), "
        f"Industry: {industry_score} ({industry_tier}), "
        f"Revenue: {rev_score}, Tech: {tech_score}, Engagement: {eng_score} "
        f"→ base={base_score}, mult={multiplier}, icp_score={icp_score} → "
        f"{'TIER ' + icp_tier if icp_tier != 'DISQUALIFIED' else 'DISQUALIFIED'}"
    )

    dq_reason = None
    if icp_tier == "DISQUALIFIED":
        dq_reason = f"icp_score {icp_score} < 40.0 threshold"

    return SegmentationRecord(
        contactId=record.contact_id,
        normalizedTitle=_normalize_title(record.title or ""),
        normalizedIndustry=_normalize_industry(record.industry or ""),
        titleTier=title_tier,
        industryTier=industry_tier,
        baseScore=base_score,
        industryMultiplier=multiplier,
        icpScore=icp_score,
        scoreBreakdown=breakdown,
        whyThisScore=why,
        icpTier=icp_tier,
        disqualificationReason=dq_reason,
        rubricCitation=f"scoring_rules.md tier thresholds: icp_score={icp_score}",
    )


# ── Batch Segmentation ────────────────────────────────────────────────────────


def segment_batch(
    task_id: str,
    records: list[EnrichmentRecord],
    tiers: Optional[TierDefinitions] = None,
    exclusions: Optional[Exclusions] = None,
) -> SegmentationOutput:
    """Score a batch of enriched records and produce SegmentationOutput."""
    if tiers is None:
        tiers = load_tier_definitions()
    if exclusions is None:
        exclusions = load_exclusions()

    scored: list[SegmentationRecord] = []
    t1 = t2 = t3 = dq = 0

    for record in records:
        result = score_contact(record, tiers, exclusions)
        scored.append(result)

        if result.icp_tier == "1":
            t1 += 1
        elif result.icp_tier == "2":
            t2 += 1
        elif result.icp_tier == "3":
            t3 += 1
        else:
            dq += 1

    return SegmentationOutput(
        taskId=task_id,
        agent="segmentation",
        timestamp=datetime.now(timezone.utc).isoformat(),
        records=scored,
        count=len(scored),
        trace=SegmentationTrace(
            vaultFilesUsed=[
                "vault/icp/scoring_rules.md",
                "vault/icp/tier_definitions.md",
                "vault/icp/disqualification.md",
                "vault/compliance/exclusions.md",
            ],
            recordsReceived=len(records),
            tier1Count=t1,
            tier2Count=t2,
            tier3Count=t3,
            disqualifiedCount=dq,
            disqualificationApplied=True,
            exclusionsChecked=True,
        ),
    )
