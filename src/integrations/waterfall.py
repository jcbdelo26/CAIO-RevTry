"""Waterfall enrichment orchestrator.

Currently Apollo-only. BetterContact and Clay are deferred (no active
subscriptions). Their status fields are kept as SKIPPED for backward
compatibility and future reactivation.

enrichment_score = (fields_filled / 7) * 100
Grade: 90-100=READY, 70-89=PARTIAL, 50-69=MINIMAL, <50=REJECT
Null email after full waterfall = DISQUALIFIED
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from models.schemas import EnrichmentGrade, EnrichmentRecord, WaterfallStatus, WaterfallTrace
from integrations.apollo_client import ApolloClient

logger = logging.getLogger(__name__)

# The 7 enrichable fields
ENRICHABLE_FIELDS = ["email", "title", "company_name", "company_size", "industry", "revenue", "linkedin_url"]


def _compute_grade(score: int) -> EnrichmentGrade:
    if score >= 90:
        return EnrichmentGrade.READY
    elif score >= 70:
        return EnrichmentGrade.PARTIAL
    elif score >= 50:
        return EnrichmentGrade.MINIMAL
    else:
        return EnrichmentGrade.REJECT


def _extract_fields(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract enrichable fields from an API response, normalizing key names."""
    result: dict[str, Any] = {}
    org = raw.get("organization") or {}

    if raw.get("email"):
        result["email"] = raw["email"]

    title = raw.get("title") or raw.get("job_title")
    if title:
        result["title"] = title

    company = (
        raw.get("company_name")
        or raw.get("organization_name")
        or org.get("name")
        or raw.get("company", {}).get("name")
    )
    if company:
        result["company_name"] = company

    size = (
        raw.get("company_size")
        or raw.get("organization_num_employees")
        or org.get("estimated_num_employees")
        or raw.get("employee_count")
    )
    if size is not None:
        try:
            result["company_size"] = int(size)
        except (ValueError, TypeError):
            pass

    industry = raw.get("industry") or org.get("industry") or raw.get("organization_industry")
    if industry:
        result["industry"] = industry

    revenue = (
        raw.get("revenue")
        or raw.get("annual_revenue")
        or org.get("organization_revenue")
        or org.get("annual_revenue")
    )
    if revenue is not None and revenue != 0.0:
        result["revenue"] = str(revenue)

    linkedin = raw.get("linkedin_url") or raw.get("linkedin")
    if linkedin:
        result["linkedin_url"] = linkedin

    return result


@dataclass
class WaterfallResult:
    contact_id: str
    fields: dict[str, Any] = field(default_factory=dict)
    apollo_status: WaterfallStatus = WaterfallStatus.SKIPPED
    bettercontact_status: WaterfallStatus = WaterfallStatus.SKIPPED
    clay_status: WaterfallStatus = WaterfallStatus.SKIPPED


class WaterfallEnricher:
    def __init__(self, apollo: Optional[ApolloClient] = None) -> None:
        self.apollo = apollo or ApolloClient()

    async def close(self) -> None:
        await self.apollo.close()

    async def enrich(
        self,
        contact_id: str,
        apollo_id: Optional[str] = None,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        company_name: Optional[str] = None,
        linkedin_url: Optional[str] = None,
    ) -> EnrichmentRecord:
        """Enrich a single contact via Apollo. Fallbacks deferred."""
        result = WaterfallResult(contact_id=contact_id)
        merged: dict[str, Any] = {}

        # Seed with whatever we already have
        if email:
            merged["email"] = email
        if first_name:
            merged["first_name"] = first_name
        if last_name:
            merged["last_name"] = last_name
        if company_name:
            merged["company_name"] = company_name
        if linkedin_url:
            merged["linkedin_url"] = linkedin_url

        # Step 1: Apollo (primary — only active enrichment source)
        try:
            raw = await self.apollo.get_person_detail(
                apollo_id=apollo_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                organization_name=company_name,
                linkedin_url=linkedin_url,
            )
            extracted = _extract_fields(raw.get("person", raw))
            if extracted:
                result.apollo_status = WaterfallStatus.HIT
                for k, v in extracted.items():
                    if k not in merged or merged[k] is None:
                        merged[k] = v
            else:
                result.apollo_status = WaterfallStatus.MISS
        except Exception as e:
            logger.warning(f"Apollo enrichment failed for {contact_id}: {e}")
            result.apollo_status = WaterfallStatus.MISS

        # Step 2: BetterContact — DEFERRED (no active subscription)
        # result.bettercontact_status remains SKIPPED

        # Step 3: Clay — DEFERRED (webhook/table model, not sync API)
        # result.clay_status remains SKIPPED

        # Calculate enrichment score
        fields_filled = sum(
            1 for f in ENRICHABLE_FIELDS if merged.get(f) is not None
        )
        fields_total = len(ENRICHABLE_FIELDS)
        enrichment_score = round((fields_filled / fields_total) * 100)
        enrichment_grade = _compute_grade(enrichment_score)

        return EnrichmentRecord(
            contactId=contact_id,
            email=merged.get("email"),
            title=merged.get("title"),
            companyName=merged.get("company_name"),
            companySize=merged.get("company_size"),
            industry=merged.get("industry"),
            revenue=merged.get("revenue"),
            linkedinUrl=merged.get("linkedin_url"),
            enrichmentScore=enrichment_score,
            enrichmentGrade=enrichment_grade,
            fieldsFilled=fields_filled,
            fieldsTotal=fields_total,
            waterfallTrace=WaterfallTrace(
                apollo=result.apollo_status,
                bettercontact=result.bettercontact_status,
                clay=result.clay_status,
            ),
        )
