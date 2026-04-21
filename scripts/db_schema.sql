-- LeadOS PostgreSQL Schema
-- Run once: psql $LEADOS_DB_URL -f scripts/db_schema.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── LEADS ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           TEXT UNIQUE NOT NULL,
    first_name      TEXT,
    last_name       TEXT,
    title           TEXT,
    company         TEXT,
    company_revenue NUMERIC,          -- USD ARR estimate
    employee_count  INT,
    industry        TEXT,
    linkedin_url    TEXT,
    timezone        TEXT DEFAULT 'America/New_York',
    intent_score    NUMERIC DEFAULT 0, -- 0–1 from intent provider (6sense, Bombora, etc.)
    lead_score      NUMERIC DEFAULT 0, -- 0–1 computed by scoring agent
    tier            SMALLINT DEFAULT 0, -- 1=auto-outreach, 2=review queue, 0=unscored
    status          TEXT DEFAULT 'new', -- new | queued | sent | replied | booked | dead | snoozed
    snooze_until    TIMESTAMPTZ,
    crm_id          TEXT,             -- HubSpot/Salesforce contact ID
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── TRIGGER EVENTS ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trigger_events (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id     UUID REFERENCES leads(id) ON DELETE CASCADE,
    event_type  TEXT,   -- funding | hire | post | news | award | product_launch
    headline    TEXT,
    source_url  TEXT,
    found_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ── OUTREACH ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS outreach (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id         UUID REFERENCES leads(id) ON DELETE CASCADE,
    trigger_event_id UUID REFERENCES trigger_events(id),
    subject         TEXT,
    body            TEXT,
    variant         TEXT DEFAULT 'A',  -- for A/B testing
    scheduled_at    TIMESTAMPTZ,
    sent_at         TIMESTAMPTZ,
    opened_at       TIMESTAMPTZ,
    replied_at      TIMESTAMPTZ,
    reply_sentiment TEXT,  -- interested | not_now | unsubscribe | neutral
    reply_body      TEXT,
    sendgrid_id     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── ACTIVITY LOG ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activity_log (
    id          BIGSERIAL PRIMARY KEY,
    lead_id     UUID REFERENCES leads(id),
    agent       TEXT,   -- researcher | personalizer | deliverer | optimizer | scorer
    action      TEXT,
    detail      JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── A/B TEST PERFORMANCE ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ab_performance (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type      TEXT,
    variant         TEXT,
    sent_count      INT DEFAULT 0,
    open_count      INT DEFAULT 0,
    reply_count     INT DEFAULT 0,
    book_count      INT DEFAULT 0,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_leads_tier_status ON leads(tier, status);
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(lead_score DESC);
CREATE INDEX IF NOT EXISTS idx_outreach_lead ON outreach(lead_id);
CREATE INDEX IF NOT EXISTS idx_activity_lead ON activity_log(lead_id, created_at DESC);
