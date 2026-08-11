import { redirect } from 'next/navigation'
import { Search } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import { ROLE_OPTIONS } from '@/lib/constants'
import ProfileCard from '@/components/ProfileCard'
import type { Profile } from '@/lib/types'

export const dynamic = 'force-dynamic'

export default async function DiscoverPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; role?: string }>
}) {
  const { q, role } = await searchParams
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  let query = supabase.from('profiles').select('*').order('created_at', { ascending: false })
  if (q) query = query.or(`full_name.ilike.%${q}%,headline.ilike.%${q}%`)
  if (role) query = query.contains('roles', [role])

  const { data: profiles, error } = await query.returns<Profile[]>()

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-6">
        <h1 className="font-display text-2xl font-semibold text-ink-50">Discover</h1>
        <p className="text-sm text-ink-400 mt-1">Find cast and crew across every role.</p>
      </div>

      <form className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-500" />
          <input
            type="text"
            name="q"
            defaultValue={q}
            placeholder="Search by name or headline…"
            className="w-full rounded-lg bg-ink-900 border border-ink-700 pl-9 pr-3.5 py-2.5 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500"
          />
        </div>
        <select
          name="role"
          defaultValue={role ?? ''}
          className="rounded-lg bg-ink-900 border border-ink-700 px-3.5 py-2.5 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500"
        >
          <option value="">All roles</option>
          {ROLE_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="rounded-lg bg-gold-500 hover:bg-gold-400 text-ink-950 font-semibold text-sm px-5 py-2.5 transition-colors"
        >
          Search
        </button>
      </form>

      {error && (
        <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
          Couldn&apos;t load profiles: {error.message}
        </p>
      )}

      {!error && profiles?.length === 0 && (
        <p className="text-sm text-ink-500 text-center py-16">
          No profiles match your search yet.
        </p>
      )}

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {profiles?.map((profile) => (
          <ProfileCard key={profile.id} profile={profile} />
        ))}
      </div>
    </div>
  )
}
