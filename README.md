# Callsheet

A LinkedIn-style network for film industry professionals — actors, directors,
producers, cinematographers, gaffers, light boys, and every other role on set.
Built with Next.js, Tailwind CSS, and Supabase.

## What's here (MVP)

- Email/password sign up and login
- Onboarding: name, headline, location, bio, photo, and multi-select roles
- A searchable, filterable directory of profiles (`/discover`)
- Public profile pages with filmography/credits
- Connect requests (send, accept, decline, remove)
- Editable profile + filmography management (`/settings`)

Not built yet, by design (see the original scope discussion): a feed/posts,
in-app messaging, a casting/job board, and endorsements. The data model
(`supabase/schema.sql`) doesn't preclude adding these later.

## Setup

### 1. Create a Supabase project

Go to [supabase.com](https://supabase.com), create a free project, and note
your **Project URL** and **anon public key** (Project Settings → API).

### 2. Run the database schema

Open the Supabase SQL Editor and run the contents of
[`supabase/schema.sql`](supabase/schema.sql). This creates the `profiles`,
`credits`, and `connections` tables with row-level security policies.

### 3. Create the avatars storage bucket

Storage → New bucket → name it `avatars` → toggle **Public bucket** on.
Then uncomment and run the storage policies at the bottom of
`supabase/schema.sql` (they're commented out because the bucket must exist
first).

### 4. Set environment variables

Copy `.env.local.example` to `.env.local` and fill in your project's URL and
anon key:

```bash
cp .env.local.example .env.local
```

```
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

The anon key is safe to expose client-side — it's designed for that, and the
row-level security policies in the schema are what actually protect the data.

### 5. Run it

```bash
npm install
npm run dev
```

## Deploying

Add the same two environment variables in your hosting provider's dashboard
(e.g. Vercel → Project Settings → Environment Variables), then deploy as a
normal Next.js app — no other config needed.

If using email confirmation (Supabase's default), add your production URL to
Supabase → Authentication → URL Configuration → Redirect URLs, e.g.
`https://your-domain.com/auth/callback`.

## Project structure

- `app/` — pages and server actions (`app/actions.ts`)
- `components/` — shared UI
- `lib/constants.ts` — the list of film industry roles and project types
- `lib/supabase/` — browser/server Supabase clients and the session-refresh
  middleware used by `proxy.ts`
- `supabase/schema.sql` — database schema, RLS policies, and storage policies
