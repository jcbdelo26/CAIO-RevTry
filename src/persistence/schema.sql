CREATE TABLE IF NOT EXISTS conversation_summaries (
    contact_id TEXT PRIMARY KEY,
    ghl_contact_id TEXT NOT NULL,
    email TEXT,
    payload_json JSONB NOT NULL,
    scanned_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversation_analyses (
    contact_id TEXT PRIMARY KEY,
    source_conversation_id TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    analyzed_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS followup_drafts (
    draft_id TEXT PRIMARY KEY,
    contact_id TEXT NOT NULL,
    ghl_contact_id TEXT,
    source_conversation_id TEXT NOT NULL,
    business_date DATE NOT NULL,
    generation_run_id TEXT NOT NULL,
    status TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    approved_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    rejection_reason TEXT,
    dispatched_at TIMESTAMPTZ,
    send_failed_at TIMESTAMPTZ,
    dispatch_error TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS followup_drafts_contact_conversation_business_date_idx
ON followup_drafts (contact_id, source_conversation_id, business_date);

CREATE TABLE IF NOT EXISTS daily_briefings (
    date DATE PRIMARY KEY,
    payload_json JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS dispatch_log (
    id BIGSERIAL PRIMARY KEY,
    contact_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    draft_id TEXT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS sent_hashes (
    draft_hash TEXT PRIMARY KEY,
    sent_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS rate_limit_counters (
    business_date DATE NOT NULL,
    channel TEXT NOT NULL,
    count INTEGER NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (business_date, channel)
);

CREATE TABLE IF NOT EXISTS circuit_breakers (
    integration TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    consecutive_failures INTEGER NOT NULL,
    tripped_at TIMESTAMPTZ,
    last_failure TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS feedback_events (
    id BIGSERIAL PRIMARY KEY,
    draft_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload_json JSONB NOT NULL
);
