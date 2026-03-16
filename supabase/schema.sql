-- =============================================================
-- Job Search AI Agent — Supabase schema
-- Run this in your Supabase SQL Editor (Dashboard → SQL Editor)
-- =============================================================

-- 1. Profiles (extends auth.users 1:1)
create table public.profiles (
  id         uuid references auth.users(id) on delete cascade primary key,
  name       text,
  email      text,
  phone      text,
  linkedin   text,
  location   text,
  experience jsonb default '[]'::jsonb,
  projects   jsonb default '[]'::jsonb,
  certifications jsonb default '[]'::jsonb,
  education  jsonb default '[]'::jsonb,
  skills     jsonb default '[]'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- 2. Search criteria (one row per user)
create table public.search_criteria (
  id               uuid default gen_random_uuid() primary key,
  user_id          uuid references auth.users(id) on delete cascade unique not null,
  keywords         jsonb default '[]'::jsonb,
  locations        jsonb default '[]'::jsonb,
  experience_levels jsonb default '[]'::jsonb,
  job_types        jsonb default '[]'::jsonb,
  exclude_terms    jsonb default '[]'::jsonb,
  created_at       timestamptz default now(),
  updated_at       timestamptz default now()
);

-- 3. Jobs (per-user, from manual upload or agent search)
create table public.jobs (
  id               uuid default gen_random_uuid() primary key,
  user_id          uuid references auth.users(id) on delete cascade not null,
  title            text not null,
  company          text not null,
  location         text,
  description      text,
  url              text,
  posted_date      text,
  salary_range     text,
  job_type         text,
  source           text,                       -- 'jsearch', 'adzuna', 'manual'
  added_by         text not null default 'user'
                     check (added_by in ('user', 'agent')),
  relevance_score  real,
  status           text not null default 'not_applied'
                     check (status in (
                       'not_applied','interested','applied',
                       'interviewing','rejected','offered'
                     )),
  resume_text      text,
  cover_letter_text text,
  notes            text,
  created_at       timestamptz default now(),
  updated_at       timestamptz default now()
);

-- Indexes
create index idx_jobs_user_id    on public.jobs (user_id);
create index idx_jobs_created_at on public.jobs (created_at desc);
create index idx_jobs_status     on public.jobs (user_id, status);

-- Prevent exact duplicate jobs per user
create unique index idx_jobs_unique
  on public.jobs (user_id, title, company, url);


-- =============================================================
-- Triggers
-- =============================================================

-- Auto-update updated_at
create or replace function public.handle_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger set_profiles_updated_at
  before update on public.profiles
  for each row execute function public.handle_updated_at();

create trigger set_search_criteria_updated_at
  before update on public.search_criteria
  for each row execute function public.handle_updated_at();

create trigger set_jobs_updated_at
  before update on public.jobs
  for each row execute function public.handle_updated_at();

-- Auto-create profile row when a new user signs up
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email);
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();


-- =============================================================
-- Row Level Security
-- =============================================================

alter table public.profiles        enable row level security;
alter table public.search_criteria enable row level security;
alter table public.jobs            enable row level security;

-- Profiles: read + update own row
create policy "Users can view own profile"
  on public.profiles for select using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update using (auth.uid() = id);

-- Search criteria: full CRUD on own rows
create policy "Users can view own criteria"
  on public.search_criteria for select using (auth.uid() = user_id);

create policy "Users can insert own criteria"
  on public.search_criteria for insert with check (auth.uid() = user_id);

create policy "Users can update own criteria"
  on public.search_criteria for update using (auth.uid() = user_id);

-- Jobs: full CRUD on own rows
create policy "Users can view own jobs"
  on public.jobs for select using (auth.uid() = user_id);

create policy "Users can insert own jobs"
  on public.jobs for insert with check (auth.uid() = user_id);

create policy "Users can update own jobs"
  on public.jobs for update using (auth.uid() = user_id);

create policy "Users can delete own jobs"
  on public.jobs for delete using (auth.uid() = user_id);
