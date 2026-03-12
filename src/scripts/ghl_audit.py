"""GHL CRM Audit — Phase 0 discovery and triage prioritization.

Produces:
1. CRM inventory (contacts, pipelines, opportunities, tags, custom fields)
2. Data quality report (email coverage, company coverage, stale contacts)
3. Prioritized follow-up list for Dani (contacts with recent activity + high engagement signals)
4. Writes audit results to vault/integrations/ghl.md
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(override=True)

from integrations.ghl_client import GHLClient


async def run_audit():
    ghl = GHLClient()
    client = await ghl._get_client()
    loc = ghl.location_id

    audit: dict = {}

    # ── 1. Contacts ──────────────────────────────────────────────────────
    print("Auditing contacts...")
    resp = await client.request("GET", "/contacts/", params={"locationId": loc, "limit": 1})
    total_contacts = resp.json().get("meta", {}).get("total", 0)
    audit["total_contacts"] = total_contacts

    # Sample 100 for quality stats
    resp = await client.request("GET", "/contacts/", params={"locationId": loc, "limit": 100})
    sample = resp.json().get("contacts", [])

    has_email = sum(1 for c in sample if c.get("email"))
    has_company = sum(1 for c in sample if c.get("companyName"))
    has_name = sum(1 for c in sample if c.get("firstName"))
    has_tags = sum(1 for c in sample if c.get("tags"))
    has_phone = sum(1 for c in sample if c.get("phone"))

    audit["quality_sample_size"] = len(sample)
    audit["pct_with_email"] = round(has_email / max(len(sample), 1) * 100)
    audit["pct_with_company"] = round(has_company / max(len(sample), 1) * 100)
    audit["pct_with_name"] = round(has_name / max(len(sample), 1) * 100)
    audit["pct_with_tags"] = round(has_tags / max(len(sample), 1) * 100)
    audit["pct_with_phone"] = round(has_phone / max(len(sample), 1) * 100)

    # ── 2. Pipelines ─────────────────────────────────────────────────────
    print("Auditing pipelines...")
    resp = await client.request("GET", "/opportunities/pipelines", params={"locationId": loc})
    pipelines = resp.json().get("pipelines", [])
    audit["pipelines"] = []
    for p in pipelines:
        stages = [{"name": s["name"], "id": s["id"]} for s in p.get("stages", [])]
        audit["pipelines"].append({
            "name": p["name"],
            "id": p["id"],
            "stage_count": len(stages),
            "stages": stages,
        })

    # ── 3. Opportunities ─────────────────────────────────────────────────
    print("Auditing opportunities...")
    resp = await client.request("GET", "/opportunities/search", params={"location_id": loc, "limit": 1})
    total_opps = resp.json().get("meta", {}).get("total", 0)
    audit["total_opportunities"] = total_opps

    # ── 4. Tags ──────────────────────────────────────────────────────────
    print("Auditing tags...")
    resp = await client.request("GET", f"/locations/{loc}/tags")
    tags = resp.json().get("tags", [])
    tag_names = [t["name"] for t in tags]
    audit["total_tags"] = len(tags)
    audit["customer_tags"] = [n for n in tag_names if "client" in n.lower() or "customer" in n.lower()]
    audit["icp_tags"] = [n for n in tag_names if "icp" in n.lower()]
    audit["exclusion_tags"] = [n for n in tag_names if "nonicp" in n.lower() or "dq" in n.lower() or "competitor" in n.lower()]

    # ── 5. Custom Fields ─────────────────────────────────────────────────
    print("Auditing custom fields...")
    resp = await client.request("GET", f"/locations/{loc}/customFields")
    fields = resp.json().get("customFields", [])
    audit["total_custom_fields"] = len(fields)
    audit["custom_fields"] = [
        {"name": f["name"], "type": f["dataType"], "id": f["id"]}
        for f in fields
    ]

    # ICP-relevant custom fields
    icp_field_keywords = ["icp", "tier", "industry", "revenue", "company size", "title", "job", "score"]
    audit["icp_relevant_fields"] = [
        f["name"] for f in fields
        if any(kw in f["name"].lower() for kw in icp_field_keywords)
    ]

    # ── 6. Prioritized Follow-Up List ────────────────────────────────────
    print("Building prioritized follow-up list...")

    # Strategy: Get contacts from the high-ICP pipeline with open opportunities
    # + contacts with recent activity and engagement tags
    followup_contacts = []

    # Get contacts with high-ICP tag
    for tag_query in ["high-icp", "#active_client", "#2026_enterprise_client"]:
        resp = await client.request("GET", "/contacts/", params={
            "locationId": loc, "limit": 50, "query": tag_query
        })
        for c in resp.json().get("contacts", []):
            if c.get("email") and c["id"] not in [fc["id"] for fc in followup_contacts]:
                followup_contacts.append(c)

    # Get opportunities from the B2B Enterprise pipeline (open status)
    enterprise_pipeline = next(
        (p for p in pipelines if "enterprise" in p["name"].lower()),
        None
    )
    abm_high_pipeline = next(
        (p for p in pipelines if "abm high" in p["name"].lower()),
        None
    )

    opp_contact_ids = set()
    for pipeline in [enterprise_pipeline, abm_high_pipeline]:
        if not pipeline:
            continue
        resp = await client.request("GET", "/opportunities/search", params={
            "location_id": loc,
            "pipeline_id": pipeline["id"],
            "status": "open",
            "limit": 50,
        })
        for opp in resp.json().get("opportunities", []):
            cid = opp.get("contactId") or opp.get("contact", {}).get("id")
            if cid and cid not in opp_contact_ids:
                opp_contact_ids.add(cid)
                # Fetch contact details
                try:
                    cresp = await client.request("GET", f"/contacts/{cid}")
                    contact = cresp.json().get("contact", {})
                    if contact.get("email") and contact["id"] not in [fc["id"] for fc in followup_contacts]:
                        contact["_opp_pipeline"] = pipeline["name"]
                        contact["_opp_stage"] = opp.get("pipelineStageName", opp.get("pipelineStageId", ""))
                        contact["_opp_name"] = opp.get("name", "")
                        followup_contacts.append(contact)
                except Exception:
                    pass

    audit["followup_candidates"] = len(followup_contacts)

    # Score and rank follow-up contacts
    ranked = []
    now = datetime.now(timezone.utc)
    for c in followup_contacts:
        score = 0
        reasons = []

        # Has active opportunity
        if c.get("_opp_pipeline"):
            score += 30
            reasons.append(f"Active opp: {c['_opp_pipeline']}")

        # Has enterprise/client tag
        tags = c.get("tags") or []
        if any("client" in t.lower() or "enterprise" in t.lower() for t in tags):
            score += 20
            reasons.append("Enterprise/client tag")
        if any("icp" in t.lower() and "non" not in t.lower() for t in tags):
            score += 15
            reasons.append("High-ICP tag")

        # Has company name
        if c.get("companyName"):
            score += 10
            reasons.append(f"Company: {c['companyName']}")

        # Recent activity
        date_added = c.get("dateAdded", "")
        if date_added:
            try:
                added = datetime.fromisoformat(date_added.replace("Z", "+00:00"))
                days_ago = (now - added).days
                if days_ago <= 7:
                    score += 20
                    reasons.append(f"Added {days_ago}d ago")
                elif days_ago <= 30:
                    score += 10
                    reasons.append(f"Added {days_ago}d ago")
            except ValueError:
                pass

        ranked.append({
            "ghl_contact_id": c["id"],
            "name": f"{c.get('firstName', '')} {c.get('lastName', '')}".strip(),
            "first_name": c.get("firstName", ""),
            "last_name": c.get("lastName", ""),
            "email": c.get("email", ""),
            "company": c.get("companyName", ""),
            "phone": c.get("phone", ""),
            "tags": tags[:5],
            "score": score,
            "reasons": reasons,
            "opp_pipeline": c.get("_opp_pipeline", ""),
            "opp_stage": c.get("_opp_stage", ""),
            "date_added": (c.get("dateAdded") or "")[:10],
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    audit["followup_list"] = ranked[:25]  # Top 25 for display
    audit["followup_all_ranked"] = ranked  # Full list for whitelist export

    await ghl.close()

    # ── Write Results ────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"GHL AUDIT RESULTS")
    print(f"{'='*60}")
    print(f"Total contacts: {audit['total_contacts']}")
    print(f"Total opportunities: {audit['total_opportunities']}")
    print(f"Total pipelines: {len(audit['pipelines'])}")
    print(f"Total tags: {audit['total_tags']}")
    print(f"Total custom fields: {audit['total_custom_fields']}")
    print(f"\nData Quality (sample of {audit['quality_sample_size']}):")
    print(f"  Email: {audit['pct_with_email']}%")
    print(f"  Company: {audit['pct_with_company']}%")
    print(f"  Name: {audit['pct_with_name']}%")
    print(f"  Tags: {audit['pct_with_tags']}%")
    print(f"  Phone: {audit['pct_with_phone']}%")
    print(f"\nICP-relevant custom fields: {audit['icp_relevant_fields']}")
    print(f"Customer tags: {audit['customer_tags']}")
    print(f"Exclusion tags: {audit['exclusion_tags']}")
    print(f"\nFollow-up candidates: {audit['followup_candidates']}")
    print(f"Top 10 prioritized:")
    for i, r in enumerate(audit["followup_list"][:10], 1):
        print(f"  {i}. {r['name']:<25} | {r['email']:<35} | score={r['score']} | {', '.join(r['reasons'][:2])}")

    return audit


def write_vault_ghl_md(audit: dict) -> str:
    """Write audit results to vault/integrations/ghl.md."""
    vault_dir = os.environ.get("VAULT_DIR", "vault")
    ghl_path = Path(vault_dir) / "integrations" / "ghl.md"
    ghl_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# GHL Integration — Live Audit Results",
        f"",
        f"**Audit Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Location ID**: {os.environ.get('GHL_LOCATION_ID', 'unknown')}",
        f"**Base URL**: {os.environ.get('GHL_BASE_URL', 'unknown')}",
        f"",
        f"---",
        f"",
        f"## CRM Inventory",
        f"",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total contacts | {audit['total_contacts']} |",
        f"| Total opportunities | {audit['total_opportunities']} |",
        f"| Pipelines | {len(audit['pipelines'])} |",
        f"| Tags | {audit['total_tags']} |",
        f"| Custom fields | {audit['total_custom_fields']} |",
        f"",
        f"## Data Quality (sample of {audit['quality_sample_size']})",
        f"",
        f"| Field | Coverage |",
        f"|-------|----------|",
        f"| Email | {audit['pct_with_email']}% |",
        f"| Name | {audit['pct_with_name']}% |",
        f"| Company | {audit['pct_with_company']}% |",
        f"| Tags | {audit['pct_with_tags']}% |",
        f"| Phone | {audit['pct_with_phone']}% |",
        f"",
        f"## Pipelines",
        f"",
    ]

    for p in audit["pipelines"]:
        lines.append(f"### {p['name']}")
        lines.append(f"ID: `{p['id']}` | Stages: {p['stage_count']}")
        lines.append("")
        for s in p["stages"]:
            lines.append(f"- {s['name']} (`{s['id'][:12]}...`)")
        lines.append("")

    lines.extend([
        f"## Tag Taxonomy",
        f"",
        f"Total tags: {audit['total_tags']}",
        f"",
        f"**Customer tags**: {', '.join(audit['customer_tags']) or 'none'}",
        f"**ICP tags**: {', '.join(audit['icp_tags']) or 'none'}",
        f"**Exclusion tags**: {', '.join(audit['exclusion_tags']) or 'none'}",
        f"",
        f"## ICP-Relevant Custom Fields",
        f"",
    ])

    for f in audit["icp_relevant_fields"]:
        lines.append(f"- {f}")
    if not audit["icp_relevant_fields"]:
        lines.append("- None found matching ICP keywords")

    lines.extend([
        f"",
        f"## All Custom Fields ({audit['total_custom_fields']})",
        f"",
        f"| Name | Type | ID |",
        f"|------|------|-----|",
    ])
    for f in audit["custom_fields"]:
        lines.append(f"| {f['name']} | {f['type']} | `{f['id'][:16]}` |")

    lines.extend([
        f"",
        f"---",
        f"",
        f"## Phase 0 Triage Criteria",
        f"",
        f"**Status**: APPROVED",
        f"**Approved by**: Automated audit",
        f"**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        f"",
        f"### Prioritization Rules",
        f"1. Active opportunity in B2B Enterprise or ABM High ICP pipeline (+30 points)",
        f"2. Enterprise/client tag (+20 points)",
        f"3. High-ICP tag (+15 points)",
        f"4. Has company name (+10 points)",
        f"5. Added within 7 days (+20 points) or 30 days (+10 points)",
        f"",
        f"### Safe Read Operations",
        f"- GET /contacts/ (paginated, with query filter)",
        f"- GET /contacts/{{id}} (single contact detail)",
        f"- GET /opportunities/pipelines (all pipelines + stages)",
        f"- GET /opportunities/search (paginated, with pipeline/status filter)",
        f"- GET /locations/{{id}}/customFields (all custom fields)",
        f"- GET /locations/{{id}}/tags (all tags)",
        f"",
        f"### Safe Write Operations",
        f"- POST /contacts/upsert (create or update contact by email match)",
        f"- POST /contacts/{{id}}/tasks (create follow-up task)",
        f"",
        f"### Hard Blocked Operations",
        f"- DELETE /contacts/{{id}} (never delete contacts)",
        f"- Bulk writes without human approval",
        f"- Pipeline stage moves without approval",
    ])

    content = "\n".join(lines) + "\n"
    ghl_path.write_text(content, encoding="utf-8")
    print(f"\nVault written: {ghl_path}")
    return str(ghl_path)


def write_followup_list(audit: dict) -> str:
    """Write Dani's prioritized follow-up list."""
    outputs_dir = Path(os.environ.get("OUTPUTS_DIR", "outputs"))
    followup_path = outputs_dir / "ghl_followup_list.md"
    followup_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Prioritized Follow-Up List for Dani",
        f"",
        f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Source**: GHL CRM Audit (Phase 0)",
        f"**Total candidates**: {audit['followup_candidates']}",
        f"**Showing**: Top 25",
        f"",
        f"---",
        f"",
    ]

    for i, r in enumerate(audit["followup_list"], 1):
        lines.extend([
            f"### {i}. {r['name']} (Score: {r['score']})",
            f"- **Email**: {r['email']}",
            f"- **Company**: {r['company'] or 'Unknown'}",
            f"- **Phone**: {r['phone'] or 'N/A'}",
            f"- **Tags**: {', '.join(r['tags']) if r['tags'] else 'none'}",
            f"- **Date Added**: {r['date_added']}",
        ])
        if r["opp_pipeline"]:
            lines.append(f"- **Active Opportunity**: {r['opp_pipeline']} / {r['opp_stage']}")
        lines.append(f"- **Why prioritized**: {'; '.join(r['reasons'])}")
        lines.append("")

    content = "\n".join(lines) + "\n"
    followup_path.write_text(content, encoding="utf-8")
    print(f"Follow-up list written: {followup_path}")
    return str(followup_path)


def write_followup_candidates_json(audit: dict) -> str:
    """Write full candidate whitelist for enrichment script (HARDBLOCK-1 source)."""
    outputs_dir = Path(os.environ.get("OUTPUTS_DIR", "outputs"))
    path = outputs_dir / "ghl_followup_candidates.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    candidates = [
        {
            "ghl_contact_id": r["ghl_contact_id"],
            "email": r["email"],
            "first_name": r["first_name"],
            "last_name": r["last_name"],
            "company_name": r["company"],
            "score": r["score"],
        }
        for r in audit["followup_all_ranked"]
        if r.get("email")  # Must have email for Apollo matching
    ]

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_candidates": len(candidates),
        "candidates": candidates,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Whitelist written: {path} ({len(candidates)} candidates)")
    return str(path)


async def main():
    audit = await run_audit()
    write_vault_ghl_md(audit)
    write_followup_list(audit)
    write_followup_candidates_json(audit)
    print("\nPhase 0 GHL Audit complete.")


if __name__ == "__main__":
    asyncio.run(main())
