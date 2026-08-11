import Link from 'next/link'
import { notFound } from 'next/navigation'
import { Film, MapPin, Pencil } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import Avatar from '@/components/Avatar'
import RoleBadge from '@/components/RoleBadge'
import ConnectButton from '@/components/ConnectButton'
import type { Credit, Profile, Connection } from '@/lib/types'

export const dynamic = 'force-dynamic'

export default async function ProfilePage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const supabase = await createClient()

  const [{ data: profile }, { data: credits }, { data: auth }] = await Promise.all([
    supabase.from('profiles').select('*').eq('id', id).maybeSingle<Profile>(),
    supabase
      .from('credits')
      .select('*')
      .eq('profile_id', id)
      .order('project_year', { ascending: false })
      .returns<Credit[]>(),
    supabase.auth.getUser(),
  ])

  if (!profile) notFound()

  const currentUserId = auth.user?.id ?? null
  let connection: Connection | null = null
  if (currentUserId && currentUserId !== id) {
    const { data } = await supabase
      .from('connections')
      .select('*')
      .or(
        `and(requester_id.eq.${currentUserId},addressee_id.eq.${id}),and(requester_id.eq.${id},addressee_id.eq.${currentUserId})`
      )
      .maybeSingle<Connection>()
    connection = data
  }

  const isOwnProfile = currentUserId === id

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
      <div className="flex flex-col sm:flex-row sm:items-start gap-5">
        <Avatar name={profile.full_name} src={profile.avatar_url} size="lg" />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="font-display text-2xl font-semibold text-ink-50">
                {profile.full_name}
              </h1>
              {profile.headline && <p className="text-ink-300 mt-0.5">{profile.headline}</p>}
              {profile.location && (
                <p className="inline-flex items-center gap-1 text-sm text-ink-500 mt-1">
                  <MapPin size={13} /> {profile.location}
                </p>
              )}
            </div>

            {isOwnProfile ? (
              <Link
                href="/settings"
                className="inline-flex items-center gap-1.5 rounded-lg bg-ink-900 hover:bg-ink-800 border border-ink-700 text-ink-200 text-sm font-medium px-4 py-2 transition-colors"
              >
                <Pencil size={14} /> Edit profile
              </Link>
            ) : currentUserId ? (
              <ConnectButton
                profileId={profile.id}
                currentUserId={currentUserId}
                connection={connection}
              />
            ) : (
              <Link
                href="/login"
                className="inline-flex items-center rounded-lg bg-gold-500 hover:bg-gold-400 text-ink-950 font-semibold text-sm px-4 py-2 transition-colors"
              >
                Sign in to connect
              </Link>
            )}
          </div>

          {profile.roles.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-4">
              {profile.roles.map((role) => (
                <RoleBadge key={role} role={role} size="md" />
              ))}
            </div>
          )}
        </div>
      </div>

      {profile.bio && (
        <p className="text-sm text-ink-300 leading-relaxed mt-8 max-w-2xl">{profile.bio}</p>
      )}

      <div className="mt-10">
        <h2 className="inline-flex items-center gap-2 font-display text-lg font-semibold text-ink-50 mb-4">
          <Film size={17} className="text-gold-400" /> Filmography
        </h2>

        {!credits || credits.length === 0 ? (
          <p className="text-sm text-ink-500">No credits added yet.</p>
        ) : (
          <div className="space-y-2">
            {credits.map((credit) => (
              <div
                key={credit.id}
                className="flex items-center justify-between gap-4 bg-ink-900 border border-ink-800 rounded-xl px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="font-medium text-ink-50 truncate">{credit.project_title}</p>
                  <p className="text-xs text-ink-400 mt-0.5">
                    {credit.role_on_project}
                    {credit.project_type ? ` · ${credit.project_type}` : ''}
                  </p>
                </div>
                {credit.project_year && (
                  <span className="text-sm text-ink-500 shrink-0">{credit.project_year}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
