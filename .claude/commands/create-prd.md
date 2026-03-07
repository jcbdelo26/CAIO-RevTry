Generate a comprehensive Product Requirements Document (PRD) from our conversation context and any existing notes.

Save the PRD to `.claude/$ARGUMENTS` (default: `PRD.md` if no argument provided).

---

## PRD Generation Process

### Step 1 — Extract Requirements
Review the entire conversation history and any existing documents to identify:
- The core problem being solved
- Target users and their needs
- Key features and functionality
- Technology preferences or constraints
- Success metrics

### Step 2 — Synthesize into PRD Structure

Generate the PRD with ALL of the following sections:

```markdown
# PRD — {Project Name}

## Executive Summary
One paragraph: what is being built, for whom, and why it matters.

## Mission
The core purpose and value proposition in 1–2 sentences.

## Target Users
- **Primary**: {user type} — {their key need}
- **Secondary**: {user type} — {their key need}

## MVP Scope

### In Scope ✅
- {feature}

### Out of Scope ❌
- {explicitly excluded feature}

## User Stories

### Must Have (Phase 1)
- **US-1**: As a {user}, I want to {action} so that {benefit}

### Phase 2
- **US-N**: As a {user}, I want to {action} so that {benefit}

## Core Architecture & Patterns
- {architectural decision and rationale}

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | {tech} | {why} |
| Backend | {tech} | {why} |
| Database | {tech} | {why} |
| Auth | {tech} | {why} |
| Testing | {tech} | {why} |

## Data Models

### {ModelName}
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | uuid | PK | Primary key |

## API Specification

### {Method} {/path}
- **Purpose**: {what it does}
- **Auth**: {required/optional}
- **Input**: {Zod schema or description}
- **Output**: {response shape}

## Security & Configuration
- {security consideration}
- Environment variables: `{VAR_NAME}` — {purpose}

## Implementation Phases

### Phase 1 — {Name} (Foundation)
**Goal**: {What a user can do after this phase ships}
**Deliverables**:
- {deliverable}
**Acceptance Criteria**:
- [ ] {measurable criterion}

### Phase 2 — {Name}
[same structure]

### Phase 3 — {Name}
[same structure]

## Success Criteria
- [ ] {measurable outcome}

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| {risk} | High/Med/Low | High/Med/Low | {mitigation} |

## Future Considerations
- {post-MVP idea}

## Appendix
- {reference links, research notes}
```

### Step 3 — Quality Validation
Before saving, verify:
- [ ] All 15 sections present and filled (no `{placeholder}` text remaining)
- [ ] Every user story includes a clear benefit ("so that...")
- [ ] MVP scope is achievable (not too large for 3–5 phases)
- [ ] Technology choices are justified
- [ ] Each phase has measurable acceptance criteria
- [ ] Out of scope list is explicit and complete
- [ ] Success criteria are measurable (not vague)

### Step 4 — Save
Write to `.claude/$ARGUMENTS` (default: `.claude/PRD.md`). Confirm the file was written and show a summary of sections included.
