-- Migration: Add agent_runs table for tracking background agent cycles
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor)

create table if not exists public.agent_runs (
  id           uuid default gen_random_uuid() primary key,
  user_id      uuid references auth.users(id) on delete cascade not null,
  started_at   timestamptz default now(),
  finished_at  timestamptz,
  status       text not null default 'running'
                 check (status in ('running','completed','failed')),
  jobs_found   int default 0,
  jobs_stored  int default 0,
  error        text
);

create index if not exists idx_agent_runs_user
  on public.agent_runs (user_id, started_at desc);

alter table public.agent_runs enable row level security;

create policy "Users can view own agent runs"
  on public.agent_runs for select using (auth.uid() = user_id);

create policy "Service can insert agent runs"
  on public.agent_runs for insert with check (true);

create policy "Service can update agent runs"
  on public.agent_runs for update using (true);
