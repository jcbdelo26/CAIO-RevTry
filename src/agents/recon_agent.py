"""Recon Agent — Apollo discovery + exclusion filter + preliminary ICP scoring.

Discovers leads via Apollo search, filters against exclusions,
applies preliminary ICP scoring, and outputs ReconOutput.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from models.schemas import ReconOutput, ReconRecord, ReconTrace
from integrations.apollo_client import ApolloClient
from utils.exclusion_checker import check_exclusions
from utils.vault_loader import (
    Exclusions,
    TierDefinitions,
    load_exclusions,
    load_tier_definitions,
)
from agents.segmentation_agent import (
    classify_title,
    classify_industry,
    score_company_size,
    score_revenue,
)


async def run_recon(
    task_id: str,
    apollo: ApolloClient,
    search_params: dict[str, Any],
    tiers: Optional[TierDefinitions] = None,
    exclusions: Optional[Exclusions] = None,
    max_pages: int = 10,
) -> ReconOutput:
    """Run lead discovery via Apollo and produce preliminary scored output."""
    if tiers is None:
        tiers = load_tier_definitions()
    if exclusions is None:
        exclusions = load_exclusions()

    all_people: list[dict[str, Any]] = []
    page = 1

    # Paginate through Apollo results
    while page <= max_pages:
        result = await apollo.search_people(
            person_titles=search_params.get("person_titles"),
            person_seniorities=search_params.get("person_seniorities"),
            organization_num_employees_ranges=search_params.get("organization_num_employees_ranges"),
            q_organization_keyword_tags=search_params.get("q_organization_keyword_tags"),
            page=page,
            per_page=25,
        )
        people = result.get("people", [])
        all_people.extend(people)

        pagination = result.get("pagination", {})
        if not pagination.get("has_more", False) or not people:
            break
        page += 1

    records_before_filter = len(all_people)
    records_excluded = 0
    records_dq = 0
    records: list[ReconRecord] = []

    for person in all_people:
        email = person.get("email") or None
        first_name = person.get("first_name", "")
        # Apollo basic plan may obfuscate last_name as "last_name_obfuscated"
        last_name = person.get("last_name") or person.get("last_name_obfuscated", "") or ""

        # Must have at least first_name + company to be useful for enrichment
        company = person.get("organization") or {}
        company_name = company.get("name", "")
        if not first_name or not company_name:
            records_excluded += 1
            continue

        # Check exclusions (only if email is known)
        if email:
            exc = check_exclusions(email, exclusions)
            if exc.is_blocked:
                records_excluded += 1
                continue

        title = person.get("title", "")
        company_size = company.get("estimated_num_employees")
        industry = company.get("industry") or ""
        revenue = company.get("annual_revenue")
        linkedin_url = person.get("linkedin_url") or None
        apollo_id = person.get("id")

        # Preliminary scoring
        title_tier = classify_title(title, tiers)
        industry_tier = classify_industry(industry, tiers)

        size_score = score_company_size(company_size)
        title_score = tiers.title_points.get(title_tier, 0)
        industry_score = tiers.industry_points.get(industry_tier, 0)
        rev_score = score_revenue(str(revenue) if revenue else None)

        base_score = size_score + title_score + industry_score + rev_score

        title_mult = tiers.industry_multipliers.get(title_tier, 0.8)
        industry_mult = tiers.industry_multipliers.get(industry_tier, 0.8)
        multiplier = max(title_mult, industry_mult)

        icp_score = round(base_score * multiplier, 1)

        if icp_score >= 80.0:
            icp_tier = "1"
        elif icp_score >= 60.0:
            icp_tier = "2"
        elif icp_score >= 40.0:
            icp_tier = "3"
        else:
            records_dq += 1
            continue  # Filter out DQ from recon output

        breakdown = f"baseScore({base_score}) x industryMultiplier({multiplier}) = icpScore({icp_score})"
        why = (
            f"Size: {size_score}, Title: {title_score} ({title_tier}), "
            f"Industry: {industry_score} ({industry_tier}), Revenue: {rev_score} "
            f"→ base={base_score}, mult={multiplier}, icp_score={icp_score} → TIER {icp_tier}"
        )

        records.append(ReconRecord(
            firstName=first_name,
            lastName=last_name,
            title=title,
            companyName=company_name,
            email=email,
            linkedinUrl=linkedin_url,
            companySize=company_size,
            industry=industry or None,
            apolloId=apollo_id,
            icpTier=icp_tier,
            baseScore=base_score,
            industryMultiplier=multiplier,
            icpScore=icp_score,
            whyThisScore=why,
            scoreBreakdown=breakdown,
        ))

    return ReconOutput(
        taskId=task_id,
        agent="recon",
        timestamp=datetime.now(timezone.utc).isoformat(),
        records=records,
        count=len(records),
        trace=ReconTrace(
            vaultFilesUsed=[
                "vault/icp/scoring_rules.md",
                "vault/icp/tier_definitions.md",
                "vault/icp/disqualification.md",
                "vault/compliance/exclusions.md",
            ],
            exclusionsChecked=True,
            disqualificationApplied=True,
            recordsFoundBeforeFilter=records_before_filter,
            recordsExcluded=records_excluded,
            recordsDisqualifiedCount=records_dq,
        ),
    )
