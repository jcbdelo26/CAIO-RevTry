# GHL Integration — Live Audit Results

**Audit Date**: 2026-03-09 19:45 UTC (Task 15 capability audit)
**Validated**: 2026-03-10 (Task 16 — quality-guard-20260310-004838246-bFye)
**Location ID**: FgaFLGYrbGZSBVprTkhR
**Base URL**: https://services.leadconnectorhq.com

---

## CRM Inventory

| Metric | Count | Source |
|--------|-------|--------|
| Total contacts | 6892 | ghl_list_contacts (live, 2026-03-09) |
| Total opportunities | 1262 | ghl_list_opportunities (live, 2026-03-09) |
| Pipelines | 9 | ghl_list_pipelines (incl. RevTry Smoke) |
| Tags (in scanned contacts) | 14 unique | 5000 contacts scanned |
| Tags (total in GHL account) | 190 | Prior audit |
| Custom fields | 91 | ghl_list_custom_fields (live, 2026-03-09) |

## Data Quality (5000 contacts scanned — 50 pages)

| Field | Population | Rate | Assessment |
|-------|-----------|------|------------|
| email | 4800 | 96.0% | Strong |
| firstName | 850 | 17.0% | Poor |
| lastName | 850 | 17.0% | Poor |
| phone | 550 | 11.0% | Poor |
| companyName | 150 | 3.0% | Very poor |
| tags | 4850 | 97.0% | Strong |
| dateLastActivity | 0 | 0.0% | Not returned by list endpoint |
| source | 500 | 10.0% | Poor |
| dateUpdated | 5000 | 100.0% | Complete |
| customFields | 0 | 0.0% | Not returned in list view |

**Note**: dateLastActivity is not returned by ghl_list_contacts. Stale contact count (5000) uses null=stale policy. dateUpdated (100% coverage) includes system-triggered updates and is not a reliable human-activity proxy.

## Pipelines

### 23 Day AI Ownership Clarity Campaign
ID: `DVYFkcxZPGBHgywcyRxn` | Stages: 4

- New Lead (`3366f33a-859...`)
- Engaged (`5de6d1f7-90d...`)
- Qualified (`96f75d34-e24...`)
- Nurture (`1289371d-55d...`)

### Affiliate / Referral Related
ID: `BwNFeynBfWeUO4ylbOWl` | Stages: 4

- Referral Recieved (`33fb29cb-f9f...`)
- Intro Made (`33e9aaab-2dd...`)
- Relationship Nurture (`cdfdd304-13c...`)
- Closed - No Sales Intent (`140bc830-bae...`)

### B2B Enterprise/Executive CAIO Placement Pipeline
ID: `i3YahAxsfHOKr5UdktBd` | Stages: 10

- New Lead (`153fecc8-5a1...`)
- First Contact Atempt (`f09a91b0-941...`)
- Connection Made (`20c31594-76d...`)
- Discovery Scheduled (`eab329d8-a38...`)
- Discovery Completed (`f7810da0-0cc...`)
- Proposal / Agreement Sent (`cf048a2d-a5f...`)
- Negotiation / Final Review (`f06801a3-c30...`)
- Closed Won (`352fcdfb-4bf...`)
- Closed Lost (`1f287d0b-775...`)
- CAIO Team Onboarding Initiated (`b280cc06-0ac...`)

### B2B clients onboarding pipeline
ID: `gXRUjITeidBWlbzoUXmK` | Stages: 9

- Prospect (`e4c3b1d9-1f3...`)
- Signed NDA (`2624599f-105...`)
- Onboarding Call Scheduled (`20bd7560-214...`)
- Active Core Client (`6d9c8b1c-4ff...`)
- Active Client – Plus (`808f0e41-dc5...`)
- Active Client – Private (`05b9fdbd-602...`)
- Active Client – On-Site (`6dc1d76d-103...`)
- Active Client – Enterprise (`cc984fbd-7c2...`)
- Renewal (`3e3d6914-268...`)

### B2C Reactivation
ID: `hQpvPAB0uizXBLFchMQb` | Stages: 4

- In Sequence (`7e2b9613-1b2...`)
- Replied (`fe316fd4-300...`)
- Video Nurture - Layer A (`667dce8e-e82...`)
- Exited (`954a4236-276...`)

### CAIO ABM High ICP Pipeline v1
ID: `cWKBvztlmL4ekBnLa7vO` | Stages: 9

- New Lead - Website (`187bc29a-ec6...`)
- First Contact Attempted (`a25a95ff-8e1...`)
- Connected (`a30f159d-9b8...`)
- Nurture Active (`4bcd125e-a62...`)
- Email Nurture Replied (`213a430f-116...`)
- Qualified (`aa743004-9f7...`)
- Proposal Sent (`9b39cee4-65b...`)
- Email Nurture Done (`36641141-87e...`)
- Not Interested (`580dd62a-e20...`)

### CAIO ABM Low/Medium ICP Pipeline v1
ID: `dhaXIRpslzOALi0WUSlV` | Stages: 7

- New Lead - Speed to Lead Active (`47ff4185-c48...`)
- First Touch Complete (`b1f69f01-cdd...`)
- Follow up - Active (`8479d21c-075...`)
- Connected - Discovery (`2f13b233-95c...`)
- Email Nurture Replied (`425c9a3f-65e...`)
- Community Invited (`b54ef57d-faa...`)
- Not Interested (`9048d05d-0f2...`)

### Vistage/Event Sales Pipeline
ID: `17OzkdzBHcc0gK5w7JNX` | Stages: 8

- Lead Captured (Form Submitted) (`d9dacdce-e90...`)
- Report Review Scheduled (`b3ae79f2-e62...`)
- Report Review Completed (`7a9505a4-500...`)
- Strategy Call Scheduled (Closer) (`eea15429-c99...`)
- Contract Sent (`79e83382-778...`)
- Closed Won (`69853cdf-686...`)
- Closed Lost (`a0e82ee4-b21...`)
- Recycle/Nurture (`36be94bf-91b...`)

## Tag Taxonomy

Total tags: 190

**Customer tags**: #2026_enterprise_client, #active_client
**ICP tags**: #nonicp, high-icp-lead-engaged, icp-low ❌
**Exclusion tags**: #nonicp

## ICP-Relevant Custom Fields

- Company Title
- Job Title 
- Industry
- Title / Position
- Annual Revenue Band
- ICP Fit Assessment
- Company Size
- intent_score

## All Custom Fields (79)

| Name | Type | ID |
|------|------|-----|
| Company Title | TEXT | `0mwiIeF04hWyEedT` |
| personal_email | TEXT | `12y3svcUy8KjZ5xP` |
| Top Pain Point | LARGE_TEXT | `1UU2aSqqqa8hEIFQ` |
| Job Title  | TEXT | `2PWKam5XwqDwrKvE` |
| Industry | TEXT | `2Q4M1UxHwjVAJucl` |
| Notes | LARGE_TEXT | `2a2efhazQYzmv6kI` |
| RB2B - Page Captured From | TEXT | `4858ihIa7e3mmWGu` |
| Current AI Adoption Level | RADIO | `4H0g26lSnqHC1Geq` |
| Preferred AI Training Offer | RADIO | `4jg7yG0H3wFU1FO5` |
| Title / Position | TEXT | `50sVdErjfnm5BDDV` |
| How were you introduced or trained to use AI tools? | RADIO | `5XEAWg57gPfJIHRv` |
| Manager Review of AI Outputs | RADIO | `6Ujj1weLDiJNcMNr` |
| Profile Photo URL | TEXT | `6fZLZebNCdA5ruaF` |
| YPO Event Location | TEXT | `6qRV3xnd0z2t78So` |
| Competitor AI Adoption % | RADIO | `9KLZa1tBdl1E8tVT` |
| Contact Type | SINGLE_OPTIONS | `9W9tuteoy6aLVw2a` |
| bucket | MULTIPLE_OPTIONS | `9yJwZhPLhGZrvc2V` |
| AI Confidence Level | RADIO | `B2mIgn6AA7kqYncW` |
| AI Tools in Daily Use | CHECKBOX | `CUE7FIY0Jkb8Pn1b` |
| Annual Revenue Band | RADIO | `DEAAh2lO6nKpfQeX` |
| company_description | LARGE_TEXT | `E7Drfnsh4hPszeqI` |
| Current AI Adoption Stage | TEXT | `E7w0QUXNzW4kw9cb` |
| Lead Created Date | TEXT | `HgHIv63MXy0iNpSt` |
| Biggest AI Challenge | TEXT | `I6dOkZHtM58G9iYb` |
| Company LinkedIn URL | TEXT | `JD6fPoBdO5s5KJGJ` |
| YPO Event Date | TEXT | `JFI1FXrRNz9TIsAI` |
| Twitter URL | TEXT | `JoWQqFWVUYc0cxlp` |
| Phone Validation Status | TEXT | `KRWgGJJ8WurqTQ0S` |
| Integration of AI into Core Systems | RADIO | `KtFctJEydxd10DoD` |
| AI Strategy Owner | RADIO | `LUrsxc85pHxgZGpV` |
| AI Opportunities | CHECKBOX | `MXDG2KW0yiSfI3cf` |
| Company Short Description | LARGE_TEXT | `MbbDkLeHz7TXvvPq` |
| AI Tool Governance (Access & Approvals) | RADIO | `NPlG4LcVoSpkmdux` |
| Phone Line Type | TEXT | `NjVrMzmZ8QmwGoq6` |
| Redacted RFI | FILE_UPLOAD | `OVX2SA3CtHEnazoR` |
| ICP Fit Assessment | TEXT | `OVXPHsYSDj2rDO7Q` |
| AI ROI Tracking | RADIO | `P223rl8ThvY822Q3` |
| Company State | TEXT | `PgjnEqdIEBPbOE2T` |
| Company Size | RADIO | `R9E1xe6m9SkzOlsp` |
| Perplexity SDR Insight | LARGE_TEXT | `RMYo4noXd60EyHM5` |
| Company City | TEXT | `S7111YaufaTpv80K` |
| Company Founded Year | TEXT | `SZfmCEH4ihtHPrVE` |
| AI Adoption Barrier | TEXT | `T6JQsKhXRKyzahyE` |
| AI Use Policy | RADIO | `T6kezRQHnJgMrx8u` |
| Frequency of AI Training | RADIO | `TQNP6eKtyDHR4t1t` |
| Company Latest Funding Stage | TEXT | `TllOc4Ti9CMCuhr8` |
| profile_headline | TEXT | `VAwhscHvfqZ1mRun` |
| rb2b_referrer | TEXT | `VkQhPAFaXdLJxUJc` |
| rb2b_captured_url | TEXT | `Vydi45jS8hrsD18p` |
| Perception of Pricing | RADIO | `WXY67WuDlmxHa0Pq` |
| AI Task Types | CHECKBOX | `XMBF4pxJgDBYAlkv` |
| Core Project Types | TEXT | `aAmcVCuEIuHxI4Jj` |
| pattern_blocker | TEXT | `cAhaFiAdEFUjuQMm` |
| LinkedIn URL | TEXT | `e3Arf3MjTvOvehFT` |
| Key Software in Daily Use | CHECKBOX | `eHidMb3CM1fe58Jj` |
| website_tech_stack | LARGE_TEXT | `fkjlnoFNZeVfEpfq` |
| preferred_lens | MULTIPLE_OPTIONS | `h52HSQGiI21EIhnn` |
| Company Total Funding | MONETORY | `hhudIriGBIADORKj` |
| AI Usage Frequency | RADIO | `hzw8arfk92gTF8zi` |
| Hallucination & Risk Mitigation | RADIO | `jfnSxAcEbCXn3p54` |
| company_profile_data | LARGE_TEXT | `jmLrk00eBzcyJecn` |
| Company Website | TEXT | `k89AW3QFWd2G4ZbR` |
| Company Logo URL | TEXT | `kqvZBFBlI3rt9Urv` |
| Comments | LARGE_TEXT | `lN8vPg0T4G51sXpC` |
| Company AI Support Level | RADIO | `nlsX3bnqvOXox4z5` |
| intent_score | TEXT | `o4wBLmEv5f9UihV7` |
| Company Snapshot Headline | LARGE_TEXT | `oPq0KMlXRUtZFlC9` |
| Standardization of Prompts & Workflows | RADIO | `olWFfVeDhMFBjF3N` |
| Primary Construction Role | TEXT | `qOtlxpEgJpjPR0FP` |
| person_bio | LARGE_TEXT | `qT0Evw6UHsEDM5fW` |
| Email Validation Status | TEXT | `s0ZcyNcIZoJlDwnN` |
| normalized_company_name | TEXT | `t2gFscw2rwpokeqa` |
| How effective do you think your current AI use is? | RADIO | `tZpNtZeb7dQA4Dot` |
| AI Improvement Areas | CHECKBOX | `trEQxJU3R7QEcEjA` |
| AI Adoption Budget | RADIO | `tuEXKohl4rqNMZm5` |
| Top KPIs | CHECKBOX | `uxbH37SMEcB7cHqw` |
| Proprietary Data in Public AI Tools | RADIO | `v1seMubnd8AVbF41` |
| Facebook URL | TEXT | `xqfLh5DLSFgclK7O` |
| rb2b_tags | TEXT | `yX5piFvANrwz8Oiw` |

---

## Phase 0 Triage Criteria

**Status**: APPROVED
**Approved by**: Chris (human approval — Task 18)
**Date**: 2026-03-10
**Revision**: v2.1 — data-informed redesign after Task 15 audit, 5 gap fixes applied

### Pre-Filter Exclusion Rules

Remove contacts before scoring:

| Rule | Condition | Rationale |
|------|-----------|-----------|
| EX-01 | Tag contains `test-seedlist-glockapps` | Test/seed data (~3,950 contacts) |
| EX-02 | Email domain in `compliance/exclusions.md` | Compliance block |
| EX-03 | Exact email in `compliance/exclusions.md` | Compliance block |
| EX-04 | No email present | Cannot follow up |
| EX-05 | Opportunity stage = "Not Interested" (any pipeline) | Explicit disinterest |
| EX-06 | Opportunity stage = "Exited" (B2C Reactivation) | Self-removed |
| EX-07 | Opportunity stage = "Closed Lost" (any pipeline) | Deal lost |
| EX-08 | Opportunity stage = "Closed - No Sales Intent" (Affiliate) | No sales intent |
| EX-09 | Opportunity in RevTry MCP Smoke Pipeline (`7cDcE1cjA7shtptHRJPY`) | Test pipeline |
| EX-10 | Opportunity stage = "Closed Won" (any pipeline) | Existing customer — not a follow-up prospect |

Estimated surviving population: ~2,400-2,500 contacts enter scoring.

### Opportunity Stage Scoring (0-50 points)

Use highest single stage score across all of a contact's opportunities:

| Points | Stage Category | Stages |
|--------|---------------|--------|
| 50 | Late-funnel deal | Proposal/Agreement Sent, Negotiation/Final Review, Contract Sent, Proposal Sent (ABM High) |
| 45 | Mid-funnel deal | Discovery Completed, Report Review Completed, Strategy Call Scheduled, Signed NDA (B2B Onboarding), Onboarding Call Scheduled (B2B Onboarding), Qualified (23-Day, ABM High) |
| 40 | Active engagement | Connected, Discovery Scheduled, Connected-Discovery, Email Nurture Replied, Report Review Scheduled, Replied (B2C Reactivation) |
| 35 | Active follow-up | Nurture Active, Follow up-Active, Engaged (23-Day), In Sequence (B2C Reactivation) |
| 25 | First touch | First Contact Attempted, First Touch Complete, Connection Made, Referral Received, Intro Made |
| 15 | New lead | New Lead, New Lead-Website, New Lead-Speed to Lead, Lead Captured, Prospect |
| 10 | Sequence exhausted | Email Nurture Done, Community Invited, Recycle/Nurture, Video Nurture - Layer A (B2C Reactivation), Relationship Nurture (Affiliate), Nurture (23-Day) |
| 5 | Existing customer | Active Client tiers, Renewal, CAIO Onboarding Initiated |
| 0 | No opportunity | Contact not in any pipeline |

**Implementation note**: Match stages by `stageId` (not stage name) to handle typos in GHL (e.g., `First Contact Atempt` in B2B Enterprise). Stage names in this table are for human reference only.

### Tag Scoring (-10 to +25 points, cumulative, clamped)

| Points | Tag | Signal |
|--------|-----|--------|
| +15 | `high` | High ICP tier |
| +10 | `email_corporate` | Corporate segment |
| +8 | `rb2b-enriched` | RB2B enrichment data available |
| +8 | `revtry-enriched` | RevTry enrichment data available |
| +7 | `23-day-active` | Active in campaign |
| +5 | `#miller-group-feb-2026` | Account-based target |
| +5 | `circle-community-invited` | Community engagement |
| -5 | `low` | Low ICP tier |
| -5 | `lowmed-abm-sequence-complete` | Low/Med sequence exhausted |
| -3 | `high-abm-sequence-complete` | High ICP sequence exhausted |
| -5 | `couldn't find caller name` | Enrichment failure |
| 0 | `email_consumer` | Consumer email (neutral) |
| 0 | Any unlisted tag | Unknown tags default to 0 |

Floor: -10 | Ceiling: +25

### Data Completeness Bonus (0-10 points)

| Points | Condition |
|--------|-----------|
| +5 | firstName AND lastName populated |
| +3 | companyName populated |
| +2 | source populated |

### Score Formula

```
totalScore = opportunityStageScore + clamp(tagScore, -10, +25) + dataCompletenessBonus
```

Range: -10 to 85

### Priority Tiers

| Tier | Score | Label | Action |
|------|-------|-------|--------|
| P1 | >= 45 | Follow Up Today | Dani contacts these today (~50-100 contacts) |
| P2 | 25-44 | Follow Up This Week | Warm leads, early engagement (~200-400) |

**Output filter**: Only P1 and P2 contacts (score >= 25) are included in the triage output. P3-P5 contacts are scored internally but excluded from the delivered list.

### API Call Sequence

1. `ghl_list_pipelines` (1 call) — build stageId → score lookup map
2. `ghl_list_opportunities` (~13 pages) — build contactId → highest stage score + exclusion set
3. `ghl_list_contacts` (up to 69 pages) — apply exclusions, score, filter to P1+P2

### Safe Read Operations
- GET /contacts/ (paginated, with query filter)
- GET /contacts/{id} (single contact detail)
- GET /opportunities/pipelines (all pipelines + stages)
- GET /opportunities/search (paginated, with pipeline/status filter)
- GET /locations/{id}/customFields (all custom fields)
- GET /locations/{id}/tags (all tags)

### Safe Write Operations
- POST /contacts/upsert (profile fields only — never tags)
- POST /contacts/{id}/tags (add-only tag append)
- POST /contacts/{id}/tasks (create follow-up task)

### Hard Blocked Operations
- DELETE /contacts/{id} (never delete contacts)
- Bulk writes without human approval
- Pipeline stage moves without approval
- Any tag removal, tag replacement, or generic contact write that includes `tags` / `tagIds`

## Verified Capability Matrix (Task 15 Audit + Task 16 Validation)

**Verified**: 2026-03-10 | **Source**: Task 15 live reads + Task 3B write evidence

| Tool | Verified | Pagination | Key Filters |
|------|----------|------------|-------------|
| ghl_list_contacts | yes | yes | query, page, page_limit |
| ghl_list_opportunities | yes | yes | pipeline_id, page, page_limit |
| ghl_list_pipelines | yes | no | — |
| ghl_list_custom_fields | yes | no | object_type |
| ghl_get_contact | yes | no | contactId, email |
| ghl_get_calendars | yes | no | — |
| ghl_get_free_slots | yes | no | calendarId, startDate, endDate, timezone |
| ghl_get_appointment | yes | no | eventId |
| ghl_get_calendar_events | yes | no | calendarId, startTime, endTime |
| ghl_create_contact | yes | no | — |
| ghl_update_contact | yes | no | — |
| ghl_add_tag | yes | no | — |
| ghl_create_opportunity | yes | no | — |
| ghl_trigger_workflow | yes | no | — |
| ghl_bulk_create_contacts | yes | no | — |
| ghl_create_appointment | yes | no | — |
| ghl_update_appointment | yes | no | — |
| ghl_delete_calendar_event | yes | no | — |

**Pagination notes**:
- ghl_list_contacts: cursor-based (startAfterId), capped at 50 pages in audit. 5000 of 6892 contacts scanned.
- ghl_list_opportunities: cursor-based, 13 pages fetched. API reports total 1262 but pagination returned 1300 items (minor overlap).
- ghl_get_calendar_events requires calendarId param (returns 422 without it).

---

## Task 3B Live MCP Verification

**Date**: 2026-03-09
**Status**: PASSED — all 18 tools verified live
**Session**: Claude Code (Opus 4.6) in `E:\Greenfield Coding Workflow\Project-RevTry\`
**Restart Pass**: 2026-03-09T13:51Z (after 6 server.py bug fixes applied in prior session)

### Tool Inventory (18/18 visible)

All 18 expected GHL MCP tools are registered and visible to Claude Code.

**Read tools (8):** `ghl_list_pipelines`, `ghl_list_custom_fields`, `ghl_list_contacts`, `ghl_list_opportunities`, `ghl_get_contact`, `ghl_get_calendars`, `ghl_get_free_slots`, `ghl_get_calendar_events`

**Write tools (10):** `ghl_create_contact`, `ghl_update_contact`, `ghl_add_tag`, `ghl_bulk_create_contacts`, `ghl_create_opportunity`, `ghl_trigger_workflow`, `ghl_create_appointment`, `ghl_get_appointment`, `ghl_update_appointment`, `ghl_delete_calendar_event`

### Read Tool Verification (8/8 PASS)

| # | Tool | Result | Evidence |
|---|------|--------|----------|
| 1 | `ghl_list_pipelines` | PASS | 9 pipelines returned (incl. RevTry MCP Smoke Pipeline `7cDcE1cjA7shtptHRJPY`) |
| 2 | `ghl_list_custom_fields` | PASS | 79+ custom fields returned for contact object type |
| 3 | `ghl_list_contacts` | PASS | 5 contacts returned, total_count=6891, cursor pagination working |
| 4 | `ghl_list_opportunities` | PASS | 5 opportunities returned, total_count=1257, cursor pagination working |
| 5 | `ghl_get_contact` (email) | PASS | Found contact `4XFxvKc2zUnnzX0zd58j` for `jcbdelossantos.va@gmail.com` |
| 6 | `ghl_get_calendars` | PASS | All location calendars returned (large response) |
| 7 | `ghl_get_free_slots` | PASS | 16 slots returned for smoke calendar `KzWHtW036U2RwCN5bWSw` on 2026-03-09 |
| 8 | `ghl_get_calendar_events` | PASS | Empty events array for smoke calendar (expected). Requires `calendarId` param. |

### Write Tool Verification (10/10 PASS)

Test contact: `jcbdelossantos.va@gmail.com` → ID `4XFxvKc2zUnnzX0zd58j`

| # | Tool | Result | Evidence |
|---|------|--------|----------|
| 1 | `ghl_create_contact` | PASS | Idempotent upsert returned existing contact, updated name to RevTry SmokeTest. traceId: `1f3016b6-7233-4d54-b454-ff9d5ddd0d8a` |
| 2 | `ghl_update_contact` | PASS | Updated lastName=SmokeTest3B, companyName=ChiefAIOfficer-Smoke. traceId: `8ebd6be0-c368-4b08-980e-a97c322547ce` |
| 3 | `ghl_add_tag` | PASS | Added tag `revtry_smoke_3b`. Tags now: `[email_consumer, revtry_smoke_3b]`. traceId: `904406b5-dcb4-4390-ac3b-38256c4196f7` |
| 4 | `ghl_create_opportunity` | PASS | Created opp `Ba5qkcI6T7R3smWVrEbF` in smoke pipeline `7cDcE1cjA7shtptHRJPY`, stage `cf2cc487` (Smoke - New Lead). traceId: `e572179f-e85f-491f-b8cd-af4f19f32a23` |
| 5 | `ghl_trigger_workflow` | PASS | Triggered workflow `b918311a-f58a-4165-8ac6-5abc33be4df4` for contact. traceId: `92c628a0-6e18-9118-bc5c-39eeb727dc66` |
| 6 | `ghl_create_appointment` | PASS | Created appointment `FVzlO5VwSQL5MnVbGxev` on smoke calendar, 17:00-17:30 ET. traceId: `d3ca27bd-f4c8-4f3d-b564-de5304b81e1f` |
| 7 | `ghl_get_appointment` | PASS | Retrieved appointment details, confirmed title and time. traceId: `0b5b9683-c8bc-4184-8008-491a73baba1f` |
| 8 | `ghl_update_appointment` | PASS | Updated title to "RevTry Smoke Test 3B - Updated". traceId: `cf7a1cbe-7965-49e9-9f30-4b7c79670a28` |
| 9 | `ghl_delete_calendar_event` | PASS | Deleted appointment `FVzlO5VwSQL5MnVbGxev`. traceId: `8e3cfa51-23f8-42e0-a741-fdb560af0837` |
| 10 | `ghl_bulk_create_contacts` | PASS | Independently verified live via the project-local MCP server copy. Created `jcds.pikot@gmail.com` -> `DB3yotXk7GxVRW6TNZ7v` and `joshbot.hitl@gmail.com` -> `TUzO5pmRPJ7xqp426wyZ`; summary `created=2`, `skipped=0`, `failed=0`. |

**Result: 10/10 tested PASS — all write tools independently verified live**

### Token Scope Verification (All Confirmed)

| Scope | Status | Evidence |
|-------|--------|----------|
| Pipelines read | CONFIRMED | `ghl_list_pipelines` returned 9 pipelines |
| Custom fields read | CONFIRMED | `ghl_list_custom_fields` returned 79+ fields |
| Contacts read | CONFIRMED | `ghl_list_contacts` returned 6891 contacts; `ghl_get_contact` found test contact |
| Contacts write | CONFIRMED | `ghl_create_contact` upserted successfully; `ghl_update_contact` modified fields |
| Tags write | CONFIRMED | `ghl_add_tag` appended `revtry_smoke_3b` to test contact |
| Opportunities write | CONFIRMED | `ghl_create_opportunity` created opp in smoke pipeline |
| Workflows write | CONFIRMED | `ghl_trigger_workflow` executed successfully |
| Calendars read | CONFIRMED | `ghl_get_calendars`, `ghl_get_free_slots`, `ghl_get_calendar_events` all returned data |
| Calendars write | CONFIRMED | Full CRUD: create → get → update → delete appointment all succeeded |

### Server Code Fixes Applied (6 total — prior session)

All fixes in `Project-RevTry/mcp-servers/ghl-mcp/server.py`:

1. **`list_contacts`** — Removed `skip` param, added `startAfterId` cursor pagination
2. **`list_opportunities`** — Removed `skip` param, added `startAfterId` cursor pagination
3. **`get_contact` (email)** — Replaced `/contacts/lookup` with `GET /contacts/?query={email}`
4. **`create_contact`** — Changed endpoint from `POST /contacts/` to `POST /contacts/upsert`
5. **`create_opportunity`** — Added `stageId→pipelineStageId` mapping and auto-default `status=open`
6. **`get_calendar_events` schema** — Made `startTime`/`endTime` required in tool definition

---

## Tag Safety Policy

- All contact tag writes are add-only
- `ghl_add_tag` is the only permitted tag mutation operation
- Generic contact upsert/update payloads may not include `tags`, `tagIds`, or any clear/remove semantics
- Generic contact updates are limited to the allowlist in `revtry/guardrails/safe_contact_write_fields.md`
- If a task appears to need tag removal, tag replacement, or blocked contact fields, escalate to Chris and stop
