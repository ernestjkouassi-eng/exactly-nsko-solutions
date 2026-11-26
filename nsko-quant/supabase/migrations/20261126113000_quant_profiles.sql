-- NSKO QUANT web demo accounts (project rluiyojdvkahfjuugqzt). Applied 26 Nov 2026 via the Supabase MCP.
-- One row per user; a signed-in user can read, add and change only their own row. No delete (the row goes when the auth user is deleted).
create table public.quant_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text check (char_length(full_name) <= 120),
  country text check (char_length(country) <= 80),
  experience text check (experience in ('new','some','experienced')),
  marketing_ok boolean not null default false,
  created_at timestamptz not null default now()
);
alter table public.quant_profiles enable row level security;
revoke all on public.quant_profiles from anon;
revoke all on public.quant_profiles from authenticated;
grant select, insert, update on public.quant_profiles to authenticated;
create policy quant_profiles_select_own on public.quant_profiles for select to authenticated using (id = (select auth.uid()));
create policy quant_profiles_insert_own on public.quant_profiles for insert to authenticated with check (id = (select auth.uid()));
create policy quant_profiles_update_own on public.quant_profiles for update to authenticated using (id = (select auth.uid())) with check (id = (select auth.uid()));
comment on table public.quant_profiles is 'NSKO QUANT web demo accounts: one row per user, own-row access only. Demo only, no trading data.';
