-- Run this in the Supabase SQL editor (Project → SQL Editor → New query) once
-- your project is created. Then create a public "avatars" storage bucket
-- (Storage → New bucket → name "avatars" → Public bucket: on) and apply the
-- storage policies at the bottom of this file.

create extension if not exists "pgcrypto";

-- Profiles ------------------------------------------------------------

create table profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  full_name text not null,
  headline text,
  bio text,
  location text,
  avatar_url text,
  roles text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table profiles enable row level security;

create policy "Profiles are publicly viewable"
  on profiles for select
  using (true);

create policy "Users can insert their own profile"
  on profiles for insert
  with check (auth.uid() = id);

create policy "Users can update their own profile"
  on profiles for update
  using (auth.uid() = id);

-- Credits (filmography) ------------------------------------------------

create table credits (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references profiles (id) on delete cascade,
  project_title text not null,
  role_on_project text not null,
  project_year int,
  project_type text,
  created_at timestamptz not null default now()
);

alter table credits enable row level security;

create policy "Credits are publicly viewable"
  on credits for select
  using (true);

create policy "Users can manage their own credits"
  on credits for all
  using (auth.uid() = profile_id)
  with check (auth.uid() = profile_id);

-- Connections -----------------------------------------------------------

create table connections (
  id uuid primary key default gen_random_uuid(),
  requester_id uuid not null references profiles (id) on delete cascade,
  addressee_id uuid not null references profiles (id) on delete cascade,
  status text not null default 'pending' check (status in ('pending', 'accepted')),
  created_at timestamptz not null default now(),
  unique (requester_id, addressee_id),
  check (requester_id <> addressee_id)
);

alter table connections enable row level security;

create policy "Users can view connections they're part of"
  on connections for select
  using (auth.uid() = requester_id or auth.uid() = addressee_id);

create policy "Users can send connection requests"
  on connections for insert
  with check (auth.uid() = requester_id);

create policy "Either side can update a connection"
  on connections for update
  using (auth.uid() = requester_id or auth.uid() = addressee_id);

create policy "Either side can remove a connection"
  on connections for delete
  using (auth.uid() = requester_id or auth.uid() = addressee_id);

-- Storage policies for the "avatars" bucket ------------------------------
-- Create the bucket first (Storage → New bucket → "avatars" → Public), then run:

-- create policy "Avatar images are publicly accessible"
--   on storage.objects for select
--   using (bucket_id = 'avatars');

-- create policy "Users can upload their own avatar"
--   on storage.objects for insert
--   with check (bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text);

-- create policy "Users can update their own avatar"
--   on storage.objects for update
--   using (bucket_id = 'avatars' and (storage.foldername(name))[1] = auth.uid()::text);
