-- LeadOS Migration 002 — Add insurance-specific columns to leads table
-- Run in Supabase Dashboard → SQL Editor → New Query → Run

-- Add insurance columns to existing leads table
ALTER TABLE leads ADD COLUMN IF NOT EXISTS raw_name TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS raw_contact TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS raw_text TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS location TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS insurance_type TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS urgency_score INTEGER;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS carrier_recommendation TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS outreach_message TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS enrichment_reasoning TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS agent_notes TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS quoted_premium FLOAT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;

-- Disable RLS on leads so service_role key can read/write freely
ALTER TABLE leads DISABLE ROW LEVEL SECURITY;

-- Grant full access to service_role
GRANT ALL ON leads TO service_role;
GRANT ALL ON leads TO authenticated;
GRANT ALL ON leads TO anon;
