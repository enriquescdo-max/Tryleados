-- LeadOS 003 — owner-only row level security
-- Run this whole file in the Supabase SQL editor AFTER 001 and 002.
-- Do not edit 002. This migration is what turns protection back on.
--
-- After it succeeds, the owner must record their login (one row):
--
--   insert into public.app_owner (id, user_id, email)
--   values (1, '<auth.users id>', '<owner email>')
--   on conflict (id) do update
--     set user_id = excluded.user_id,
--         email = excluded.email,
--         updated_at = now();
--
-- Until that row exists, signed-in browser clients see no lead rows.
-- The Railway backend uses the service_role key, which bypasses RLS.
-- The anon key must not be able to read or write leads. The anon key that
-- was committed in leadOS-login.html has to be rotated. It is still in git
-- history. Rotate the service_role key as well if it was ever copied into a
-- frontend, a ticket, or a log, then update Railway SUPABASE_SERVICE_KEY.
-- Do not commit either new key.

create table if not exists public.app_owner (
  id integer primary key check (id = 1),
  user_id uuid,
  email text,
  updated_at timestamptz default now()
);

alter table public.app_owner enable row level security;
alter table public.app_owner force row level security;
revoke all on table public.app_owner from public;
revoke all on table public.app_owner from anon;
revoke all on table public.app_owner from authenticated;

create or replace function public.current_user_is_owner()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.app_owner
    where id = 1
      and user_id is not null
      and user_id = auth.uid()
  );
$$;

revoke all on function public.current_user_is_owner() from public;
revoke all on function public.current_user_is_owner() from anon;
grant execute on function public.current_user_is_owner() to authenticated;

-- leads: 002 disabled RLS and granted anon full access. Reverse that here.
alter table public.leads enable row level security;
alter table public.leads force row level security;
revoke all on table public.leads from public;
revoke all on table public.leads from anon;
revoke all on table public.leads from authenticated;
drop policy if exists leads_owner_all on public.leads;
create policy leads_owner_all on public.leads
  for all
  to authenticated
  using (public.current_user_is_owner())
  with check (public.current_user_is_owner());
grant select, insert, update, delete on table public.leads to authenticated;

-- Other tables that hold lead or caller data. Owner sees all of it.
-- A random authenticated signup sees none of it.
alter table public.user_memory enable row level security;
alter table public.user_memory force row level security;
revoke all on table public.user_memory from public;
revoke all on table public.user_memory from anon;
revoke all on table public.user_memory from authenticated;
drop policy if exists "Users see own memory" on public.user_memory;
drop policy if exists user_memory_owner_all on public.user_memory;
create policy user_memory_owner_all on public.user_memory
  for all to authenticated
  using (public.current_user_is_owner())
  with check (public.current_user_is_owner());
grant select, insert, update, delete on table public.user_memory to authenticated;

alter table public.lead_history enable row level security;
alter table public.lead_history force row level security;
revoke all on table public.lead_history from public;
revoke all on table public.lead_history from anon;
revoke all on table public.lead_history from authenticated;
drop policy if exists "Users see own leads" on public.lead_history;
drop policy if exists lead_history_owner_all on public.lead_history;
create policy lead_history_owner_all on public.lead_history
  for all to authenticated
  using (public.current_user_is_owner())
  with check (public.current_user_is_owner());
grant select, insert, update, delete on table public.lead_history to authenticated;

alter table public.voice_call_logs enable row level security;
alter table public.voice_call_logs force row level security;
revoke all on table public.voice_call_logs from public;
revoke all on table public.voice_call_logs from anon;
revoke all on table public.voice_call_logs from authenticated;
drop policy if exists "Users see own calls" on public.voice_call_logs;
drop policy if exists voice_call_logs_owner_all on public.voice_call_logs;
create policy voice_call_logs_owner_all on public.voice_call_logs
  for all to authenticated
  using (public.current_user_is_owner())
  with check (public.current_user_is_owner());
grant select, insert, update, delete on table public.voice_call_logs to authenticated;

alter table public.conversation_history enable row level security;
alter table public.conversation_history force row level security;
revoke all on table public.conversation_history from public;
revoke all on table public.conversation_history from anon;
revoke all on table public.conversation_history from authenticated;
drop policy if exists "Users see own conversations" on public.conversation_history;
drop policy if exists conversation_history_owner_all on public.conversation_history;
create policy conversation_history_owner_all on public.conversation_history
  for all to authenticated
  using (public.current_user_is_owner())
  with check (public.current_user_is_owner());
grant select, insert, update, delete on table public.conversation_history to authenticated;
