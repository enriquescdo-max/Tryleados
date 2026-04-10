-- LeadOS Phase 1 — Supabase Tables
-- Run this entire file in Supabase Dashboard → SQL Editor → New Query → Run
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. LEADS (operational table — persists crawled leads across Railway restarts)
CREATE TABLE IF NOT EXISTS leads (
  id                  TEXT PRIMARY KEY,
  name                TEXT,
  email               TEXT,
  phone               TEXT,
  title               TEXT,
  company             TEXT,
  source              TEXT DEFAULT 'web_crawler',
  status              TEXT DEFAULT 'new',
  ai_score            INTEGER,
  ai_score_reasoning  TEXT,
  intent_signals      JSONB DEFAULT '[]',
  email_verified      BOOLEAN,
  linkedin_url        TEXT,
  created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 2. USER_MEMORY (per-user persistent context — Brain + Voice Agent read this)
CREATE TABLE IF NOT EXISTS user_memory (
  id                    UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id               UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  industry              TEXT DEFAULT 'insurance',
  icp_description       TEXT,
  target_states         TEXT[],
  avg_lead_score        FLOAT DEFAULT 0,
  total_leads_generated INT DEFAULT 0,
  total_transfers       INT DEFAULT 0,
  preferred_call_hours  TEXT DEFAULT '9am-5pm CST',
  memory_notes          TEXT,
  created_at            TIMESTAMPTZ DEFAULT NOW(),
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

-- 3. LEAD_HISTORY (every lead ever found for each user — Supabase-native version)
CREATE TABLE IF NOT EXISTS lead_history (
  id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id          UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name             TEXT,
  company          TEXT,
  phone            TEXT,
  email            TEXT,
  industry         TEXT,
  score            FLOAT,
  score_reason     TEXT,
  source           TEXT,
  status           TEXT DEFAULT 'new',
  transferred      BOOLEAN DEFAULT false,
  transfer_billed  BOOLEAN DEFAULT false,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- 4. VOICE_CALL_LOGS (every Vapi call — transcript, score, transfer outcome)
CREATE TABLE IF NOT EXISTS voice_call_logs (
  id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id           UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  lead_id           UUID REFERENCES lead_history(id) ON DELETE SET NULL,
  vapi_call_id      TEXT,
  duration_seconds  INT,
  score_before_call FLOAT,
  score_after_call  FLOAT,
  transferred       BOOLEAN DEFAULT false,
  transfer_amount   FLOAT,
  recording_url     TEXT,
  transcript        TEXT,
  call_outcome      TEXT,
  created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- 5. CONVERSATION_HISTORY (chatbot memory per user — continuity across sessions)
CREATE TABLE IF NOT EXISTS conversation_history (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  role        TEXT CHECK (role IN ('user', 'assistant')),
  content     TEXT,
  session_id  TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- P4: ROW LEVEL SECURITY — users only see their own data
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE user_memory         ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_history        ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_call_logs     ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_history ENABLE ROW LEVEL SECURITY;

-- user_memory
CREATE POLICY "Users see own memory" ON user_memory
  FOR ALL USING (auth.uid() = user_id);

-- lead_history
CREATE POLICY "Users see own leads" ON lead_history
  FOR ALL USING (auth.uid() = user_id);

-- voice_call_logs
CREATE POLICY "Users see own calls" ON voice_call_logs
  FOR ALL USING (auth.uid() = user_id);

-- conversation_history
CREATE POLICY "Users see own conversations" ON conversation_history
  FOR ALL USING (auth.uid() = user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- Indexes for common queries
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_lead_history_user_id    ON lead_history(user_id);
CREATE INDEX IF NOT EXISTS idx_lead_history_status     ON lead_history(status);
CREATE INDEX IF NOT EXISTS idx_voice_call_logs_user_id ON voice_call_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_conv_history_user_id    ON conversation_history(user_id, session_id);
CREATE INDEX IF NOT EXISTS idx_user_memory_user_id     ON user_memory(user_id);
