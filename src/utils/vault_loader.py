"""Parse vault markdown files into typed Python data structures.

Each loader reads a specific vault .md file and extracts the structured
data from its markdown tables into typed dataclasses / dicts.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def _vault_dir() -> Path:
    return Path(os.environ.get("VAULT_DIR", "vault"))


def _read_vault_file(relative_path: str) -> str:
    path = _vault_dir() / relative_path
    return path.read_text(encoding="utf-8")


# ── Exclusions ─────────────────────────────────────────────────────────────────


@dataclass
class Exclusions:
    blocked_domains: set[str]
    blocked_emails: set[str]


def load_exclusions() -> Exclusions:
    text = _read_vault_file("compliance/exclusions.md")

    domains: set[str] = set()
    emails: set[str] = set()

    # Parse blocked domains table
    in_domain_table = False
    in_email_table = False

    for line in text.splitlines():
        stripped = line.strip()

        if "Blocked Domains" in stripped and "##" in stripped:
            in_domain_table = True
            in_email_table = False
            continue
        if "Blocked Individual Emails" in stripped and "##" in stripped:
            in_email_table = True
            in_domain_table = False
            continue
        if stripped.startswith("## ") and in_email_table:
            in_email_table = False
            continue
        if stripped.startswith("## ") and in_domain_table:
            in_domain_table = False
            continue

        if not stripped.startswith("|") or stripped.startswith("|---") or stripped.startswith("| Domain") or stripped.startswith("| Email"):
            continue

        cells = [c.strip() for c in stripped.split("|")[1:-1]]
        if len(cells) < 2:
            continue

        if in_domain_table and cells[1] == "BLOCKED":
            domains.add(cells[0].lower())
        elif in_email_table and cells[2] == "BLOCKED":
            emails.add(cells[0].lower())

    return Exclusions(blocked_domains=domains, blocked_emails=emails)


# ── Scoring Rules ──────────────────────────────────────────────────────────────


@dataclass
class ScoringComponent:
    name: str
    max_points: int
    logic: dict[str, int]  # condition → points


@dataclass
class ScoringRules:
    components: list[ScoringComponent]
    max_base_score: int  # 100
    tier_thresholds: dict[str, tuple[float, float]]  # tier → (min, max)


def load_scoring_rules() -> ScoringRules:
    components = [
        ScoringComponent(
            name="company_size",
            max_points=20,
            logic={
                "101-250": 20,
                "51-100": 15,
                "251-500": 15,
                "10-50": 10,
                "501-1000": 10,
            },
        ),
        ScoringComponent(
            name="title_match",
            max_points=25,
            logic={
                "tier_1": 25,
                "tier_2": 22,
                "tier_3": 18,
                "manager": 12,
                "unmatched": 0,
            },
        ),
        ScoringComponent(
            name="industry_match",
            max_points=20,
            logic={
                "tier_1": 20,
                "tier_2": 15,
                "tier_3": 10,
                "unmatched": 0,
            },
        ),
        ScoringComponent(
            name="revenue_fit",
            max_points=15,
            logic={
                "10m-50m": 15,
                "5m-10m": 12,
                "50m-100m": 12,
                "1m-5m": 8,
                "gt_100m": 8,
                "lt_1m": 0,
                "unknown": 0,
            },
        ),
        ScoringComponent(
            name="tech_signal",
            max_points=10,
            logic={
                "active_ai_hiring": 10,
                "ai_tools_adopted": 7,
                "no_signal": 0,
            },
        ),
        ScoringComponent(
            name="engagement_signal",
            max_points=10,
            logic={
                "website_visit": 10,
                "content_download": 7,
                "social_engagement": 5,
                "none": 0,
            },
        ),
    ]

    tier_thresholds = {
        "1": (80.0, 150.0),
        "2": (60.0, 80.0),
        "3": (40.0, 60.0),
        "DISQUALIFIED": (0.0, 40.0),
    }

    return ScoringRules(
        components=components,
        max_base_score=100,
        tier_thresholds=tier_thresholds,
    )


# ── Tier Definitions ───────────────────────────────────────────────────────────


@dataclass
class TierDefinitions:
    title_buckets: dict[str, list[str]]  # tier → list of title keywords
    title_points: dict[str, int]         # tier → points
    industry_tiers: dict[str, list[str]] # tier → list of industries
    industry_points: dict[str, int]      # tier → points
    industry_multipliers: dict[str, float]
    company_size_scores: dict[str, int]  # range_key → points
    revenue_scores: dict[str, int]       # range_key → points


def load_tier_definitions() -> TierDefinitions:
    return TierDefinitions(
        title_buckets={
            "tier_1": ["ceo", "founder", "president", "coo", "owner", "managing partner"],
            "tier_2": ["cto", "cio", "chief of staff", "vp operations", "vp strategy",
                       "vp innovation", "managing director"],
            "tier_3": ["director ops", "director it", "director strategy",
                       "vp engineering", "head of ai", "head of data"],
            "manager": ["operations manager", "it manager", "project manager",
                        "general manager"],
        },
        title_points={
            "tier_1": 25,
            "tier_2": 22,
            "tier_3": 18,
            "manager": 12,
            "unmatched": 0,
        },
        industry_tiers={
            "tier_1": ["agencies", "staffing", "consulting", "law", "cpa",
                       "real estate", "e-commerce", "ecommerce"],
            "tier_2": ["b2b saas", "saas", "it services", "healthcare",
                       "financial services"],
            "tier_3": ["manufacturing", "logistics", "construction",
                       "home services"],
        },
        industry_points={
            "tier_1": 20,
            "tier_2": 15,
            "tier_3": 10,
            "unmatched": 0,
        },
        industry_multipliers={
            "tier_1": 1.5,
            "tier_2": 1.2,
            "tier_3": 1.0,
            "unmatched": 0.8,
        },
        company_size_scores={
            "101-250": 20,
            "51-100": 15,
            "251-500": 15,
            "10-50": 10,
            "501-1000": 10,
        },
        revenue_scores={
            "10m-50m": 15,
            "5m-10m": 12,
            "50m-100m": 12,
            "1m-5m": 8,
            "gt_100m": 8,
            "lt_1m": 0,
            "unknown": 0,
        },
    )


# ── Disqualification Rules ────────────────────────────────────────────────────


@dataclass
class DisqualificationRule:
    rule_id: str
    name: str
    condition: str
    action: str = "BLOCK"


def load_disqualification_rules() -> list[DisqualificationRule]:
    return [
        DisqualificationRule("DQ-001", "Too small", "<10 employees"),
        DisqualificationRule("DQ-002", "Too large", ">1,000 employees"),
        DisqualificationRule("DQ-003", "Government", "Industry = Government"),
        DisqualificationRule("DQ-004", "Non-profit", "Industry = Non-profit"),
        DisqualificationRule("DQ-005", "Education", "Industry = Education/Academia"),
        DisqualificationRule("DQ-006", "Current customer", 'GHL tag contains "Customer"'),
        DisqualificationRule("DQ-007", "Competitor", "Known competitor domain"),
        DisqualificationRule("DQ-008", "Blocked domain", "Email domain in exclusions.md"),
        DisqualificationRule("DQ-009", "Blocked email", "Exact email in exclusions.md"),
    ]


# ── Email Angles ───────────────────────────────────────────────────────────────


@dataclass
class EmailAngle:
    angle_id: str
    name: str
    applicable_tiers: list[str]
    description: str


@dataclass
class AngleMapping:
    angles: list[EmailAngle]
    tier_to_allowed: dict[str, list[str]]  # tier → list of allowed angle IDs
    tier_to_default: dict[str, str]         # tier → default angle ID


def load_email_angles() -> AngleMapping:
    angles = [
        EmailAngle(
            angle_id="ai_executive_briefing",
            name="AI Executive Briefing",
            applicable_tiers=["1"],
            description="CEO/Founder-level -- strategic AI transformation",
        ),
        EmailAngle(
            angle_id="operational_efficiency",
            name="Operational Efficiency",
            applicable_tiers=["1", "2"],
            description="Process automation, team productivity, cost reduction",
        ),
        EmailAngle(
            angle_id="tech_modernization",
            name="Tech Modernization",
            applicable_tiers=["2", "3"],
            description="AI stack adoption, integration with existing systems",
        ),
        EmailAngle(
            angle_id="competitive_edge",
            name="Competitive Edge",
            applicable_tiers=["1", "2"],
            description="Industry-specific AI use cases, competitor analysis",
        ),
        EmailAngle(
            angle_id="quick_win",
            name="Quick Win",
            applicable_tiers=["2", "3"],
            description="Low-lift AI pilots, 30-day results, minimal disruption",
        ),
    ]

    tier_to_allowed = {
        "1": ["ai_executive_briefing", "competitive_edge"],
        "2": ["operational_efficiency", "tech_modernization", "competitive_edge"],
        "3": ["tech_modernization", "quick_win"],
    }

    tier_to_default = {
        "1": "ai_executive_briefing",
        "2": "operational_efficiency",
        "3": "quick_win",
    }

    return AngleMapping(
        angles=angles,
        tier_to_allowed=tier_to_allowed,
        tier_to_default=tier_to_default,
    )


# ── Signatures ─────────────────────────────────────────────────────────────────


@dataclass
class Signatures:
    sender_name: str
    sender_title: str
    can_spam_footer: str
    booking_link: str
    banned_openers: list[str]
    subject_max_length: int
    subject_max_exclamations: int


def load_signatures() -> Signatures:
    return Signatures(
        sender_name="Dani Apgar",
        sender_title="Head of Sales, Chief AI Officer",
        can_spam_footer=(
            "Reply STOP to unsubscribe.\n"
            "Chief AI Officer Inc. | 5700 Harper Dr, Suite 210, Albuquerque, NM 87109"
        ),
        booking_link="https://caio.cx/ai-exec-briefing-call",
        banned_openers=[
            "Hope this finds you well",
            "I wanted to reach out",
            "Are you open to",
            "I came across your profile",
            "Just checking in",
            "I hope you're doing well",
            "I noticed",
            "Quick question",
        ],
        subject_max_length=60,
        subject_max_exclamations=1,
    )
