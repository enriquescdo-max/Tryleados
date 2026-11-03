-- LeadOS 004 — inbound call intake, consent ledger, drafts
-- Run this in the Supabase SQL editor AFTER 003_rls_owner_lockdown.sql.
-- These tables are owner-only from the moment they exist. Nothing here
-- disables row level security or grants the anon role access.

alter table public.leads add column if not exists phone text;
alter table public.leads add column if not exists email text;
alter table public.leads add column if not exists zip text;
alter table public.leads add column if not exists language text;
alter table public.leads add column if not exists line_of_business text;
alter table public.leads add column if not exists transcript_summary text;
alter table public.leads add column if not exists disqualifiers jsonb default '[]'::jsonb;
alter table public.leads add column if not exists callback_requested boolean default false;
alter table public.leads add column if not exists sla_started_at timestamptz;
alter table public.leads add column if not exists sla_due_at timestamptz;
alter table public.leads add column if not exists sla_alerted_at timestamptz;
alter table public.leads add column if not exists first_response_at timestamptz;
alter table public.leads add column if not exists source_call_id text;

create table if not exists public.consent_ledger (
  id uuid primary key default gen_random_uuid(),
  lead_id text,
  phone text,
  email text,
  channel text,
  source text check (source in ('call', 'web_form', 'dm', 'owner_recorded')),
  consent_text text not null,
  written boolean not null default false,
  scope text,
  evidence text,
  granted_at timestamptz not null default now(),
  revoked_at timestamptz,
  metadata jsonb default '{}'::jsonb
);

create table if not exists public.followup_drafts (
  id uuid primary key default gen_random_uuid(),
  lead_id text not null,
  body text not null,
  status text not null default 'draft' check (status in ('draft', 'approved')),
  approved_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.voice_calls (
  id uuid primary key default gen_random_uuid(),
  call_id text unique,
  lead_id text,
  from_number text,
  language text,
  line_of_business text,
  zip text,
  summary text,
  disqualifiers jsonb default '[]'::jsonb,
  disposition text,
  created_at timestamptz not null default now()
);

create index if not exists consent_ledger_phone_idx on public.consent_ledger (phone);
create index if not exists consent_ledger_lead_idx on public.consent_ledger (lead_id);
create index if not exists voice_calls_call_id_idx on public.voice_calls (call_id);

-- Owner-only. service_role bypasses row level security for the Railway API.
alter table public.consent_ledger enable row level security;
alter table public.consent_ledger force row level security;
revoke all on table public.consent_ledger from public;
revoke all on table public.consent_ledger from anon;
revoke all on table public.consent_ledger from authenticated;
drop policy if exists consent_ledger_owner_all on public.consent_ledger;
create policy consent_ledger_owner_all on public.consent_ledger
  for all to authenticated
  using (public.current_user_is_owner())
  with check (public.current_user_is_owner());
grant select, insert, update, delete on table public.consent_ledger to authenticated;

alter table public.followup_drafts enable row level security;
alter table public.followup_drafts force row level security;
revoke all on table public.followup_drafts from public;
revoke all on table public.followup_drafts from anon;
revoke all on table public.followup_drafts from authenticated;
drop policy if exists followup_drafts_owner_all on public.followup_drafts;
create policy followup_drafts_owner_all on public.followup_drafts
  for all to authenticated
  using (public.current_user_is_owner())
  with check (public.current_user_is_owner());
grant select, insert, update, delete on table public.followup_drafts to authenticated;

alter table public.voice_calls enable row level security;
alter table public.voice_calls force row level security;
revoke all on table public.voice_calls from public;
revoke all on table public.voice_calls from anon;
revoke all on table public.voice_calls from authenticated;
drop policy if exists voice_calls_owner_all on public.voice_calls;
create policy voice_calls_owner_all on public.voice_calls
  for all to authenticated
  using (public.current_user_is_owner())
  with check (public.current_user_is_owner());
grant select, insert, update, delete on table public.voice_calls to authenticated;
