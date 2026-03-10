# Apollo Integration
**Valid Through**: 2026-06-30
**Last Updated**: 2026-03-07
**Updated By**: Phase 1 setup
**Source**: Apollo.io API documentation
**Applies To**: Recon Agent, Enrichment Agent

## Purpose
Apollo.io is the primary data provider for both lead discovery (Recon) and contact enrichment. All API calls go through the RevTry Python client (`integrations/apollo_client.py`).

## API Configuration

- **Base URL**: `https://api.apollo.io/api/v1`
- **Auth**: API key passed in `X-Api-Key` request header
- **Env var**: `APOLLO_API_KEY`
- **Rate limit**: 200 requests/hour (Basic plan), higher on paid tiers
- **Timeout**: 30s per request
- **Retry**: 2x on 5xx, exponential backoff on 429

## Endpoints Used

### 1. People Search (Recon Agent)
- **Method**: `POST /mixed_people/api_search`
- **Purpose**: Discover leads matching ICP filters
- **Key parameters**:
  - `person_titles` — array of title strings (e.g., ["CEO", "Founder"])
  - `person_seniorities` — array (e.g., ["c_suite", "vp", "director"])
  - `organization_num_employees_ranges` — array (e.g., ["51,200", "201,500"])
  - `q_organization_keyword_tags` — array of industry keywords
  - `page` / `per_page` — pagination (default 25 per page)
- **Response shape**:
  ```json
  {
    "people": [{
      "first_name": "string",
      "last_name": "string",
      "title": "string",
      "email": "string|null",
      "linkedin_url": "string|null",
      "organization": {
        "name": "string",
        "estimated_num_employees": "integer|null",
        "industry": "string|null",
        "annual_revenue": "number|null"
      }
    }],
    "pagination": {
      "page": 1,
      "per_page": 25,
      "total_entries": 1500,
      "has_more": true
    }
  }
  ```

### 2. People Match (Enrichment Agent)
- **Method**: `POST /people/match`
- **Purpose**: Enrich a known contact by matching on email, name, or LinkedIn URL
- **Key parameters**:
  - `email` — email to match
  - `first_name` / `last_name` — name to match
  - `organization_name` — company to match
  - `linkedin_url` — LinkedIn profile URL
- **Response shape**:
  ```json
  {
    "person": {
      "email": "string|null",
      "title": "string|null",
      "organization_name": "string|null",
      "organization_num_employees": "integer|null",
      "industry": "string|null",
      "linkedin_url": "string|null"
    }
  }
  ```

## Field Mapping

| Apollo Field | RevTry Field | Notes |
|-------------|-------------|-------|
| `email` | `email` | RFC 5322 validated |
| `title` / `job_title` | `title` | Normalized for ICP scoring |
| `organization.name` / `organization_name` | `company_name` | |
| `organization.estimated_num_employees` / `organization_num_employees` | `company_size` | Integer |
| `organization.industry` / `industry` | `industry` | Matched against tier_definitions.md |
| `organization.annual_revenue` / `annual_revenue` | `revenue` | String with $ prefix |
| `linkedin_url` | `linkedin_url` | Full URL |

## Error Handling

| Status | Behavior |
|--------|----------|
| 200 | Success — extract fields |
| 401 | Invalid API key — STOP, escalate |
| 422 | Invalid parameters — log, skip record |
| 429 | Rate limited — backoff per Retry-After header (max 60s) |
| 5xx | Server error — retry up to 2x with exponential backoff |
| Timeout | Treat as MISS, proceed |

## Credit Usage
- People Search: 1 credit per result returned
- People Match: 1 credit per match
- Monitor credit balance via Apollo dashboard

## Do NOT Apply This File To
- BetterContact or Clay enrichment (deferred)
- GHL operations (separate integration)
- Direct Apollo UI actions

## Review Trigger
- When Apollo API version changes
- When rate limit tier changes
- When new endpoints are needed
- Quarterly during vault freshness review
