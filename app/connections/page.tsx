import Link from 'next/link'
import { redirect } from 'next/navigation'
import { Check, X } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import { removeConnection, respondToConnection } from '@/app/actions'
import Avatar from '@/components/Avatar'
import RoleBadge from '@/components/RoleBadge'
import type { Connection, Profile } from '@/lib/types'

export const dynamic = 'force-dynamic'

export default async function ConnectionsPage() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const { data: connections } = await supabase
    .from('connections')
    .select('*')
    .or(`requester_id.eq.${user.id},addressee_id.eq.${user.id}`)
    .returns<Connection[]>()

  const otherIds = Array.from(
    new Set(
      (connections ?? []).map((c) => (c.requester_id === user.id ? c.addressee_id : c.requester_id))
    )
  )

  const { data: profiles } = otherIds.length
    ? await supabase.from('profiles').select('*').in('id', otherIds).returns<Profile[]>()
    : { data: [] as Profile[] }

  const profileById = new Map((profiles ?? []).map((p) => [p.id, p]))

  const incoming = (connections ?? []).filter(
    (c) => c.status === 'pending' && c.addressee_id === user.id
  )
  const outgoing = (connections ?? []).filter(
    (c) => c.status === 'pending' && c.requester_id === user.id
  )
  const accepted = (connections ?? []).filter((c) => c.status === 'accepted')

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10 space-y-10">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink-50">Connections</h1>
        <p className="text-sm text-ink-400 mt-1">Your network, and requests waiting on you.</p>
      </div>

      {incoming.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-500 mb-3">
            Pending requests
          </h2>
          <div className="space-y-2">
            {incoming.map((c) => {
              const person = profileById.get(c.requester_id)
              if (!person) return null
              return (
                <div
                  key={c.id}
                  className="flex items-center justify-between gap-3 bg-ink-900 border border-ink-800 rounded-xl px-4 py-3"
                >
                  <PersonRow person={person} />
                  <div className="flex items-center gap-2 shrink-0">
                    <form action={respondToConnection.bind(null, c.id, true)}>
                      <button className="inline-flex items-center gap-1 rounded-lg bg-gold-500 hover:bg-gold-400 text-ink-950 text-xs font-semibold px-3 py-1.5 transition-colors">
                        <Check size={13} /> Accept
                      </button>
                    </form>
                    <form action={respondToConnection.bind(null, c.id, false)}>
                      <button className="inline-flex items-center gap-1 rounded-lg bg-ink-800 hover:bg-ink-700 text-ink-300 text-xs px-3 py-1.5 transition-colors">
                        <X size={13} /> Decline
                      </button>
                    </form>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      <section>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-500 mb-3">
          Your connections ({accepted.length})
        </h2>
        {accepted.length === 0 ? (
          <p className="text-sm text-ink-500">
            No connections yet.{' '}
            <Link href="/discover" className="text-gold-400 hover:text-gold-300">
              Find people to connect with
            </Link>
            .
          </p>
        ) : (
          <div className="space-y-2">
            {accepted.map((c) => {
              const otherId = c.requester_id === user.id ? c.addressee_id : c.requester_id
              const person = profileById.get(otherId)
              if (!person) return null
              return (
                <div
                  key={c.id}
                  className="flex items-center justify-between gap-3 bg-ink-900 border border-ink-800 rounded-xl px-4 py-3"
                >
                  <PersonRow person={person} />
                  <form action={removeConnection.bind(null, c.id)}>
                    <button className="text-xs text-ink-500 hover:text-red-400 transition-colors shrink-0">
                      Remove
                    </button>
                  </form>
                </div>
              )
            })}
          </div>
        )}
      </section>

      {outgoing.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-500 mb-3">
            Sent requests
          </h2>
          <div className="space-y-2">
            {outgoing.map((c) => {
              const person = profileById.get(c.addressee_id)
              if (!person) return null
              return (
                <div
                  key={c.id}
                  className="flex items-center justify-between gap-3 bg-ink-900 border border-ink-800 rounded-xl px-4 py-3"
                >
                  <PersonRow person={person} />
                  <span className="text-xs text-ink-500 shrink-0">Waiting</span>
                </div>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}

function PersonRow({ person }: { person: Profile }) {
  return (
    <Link href={`/profile/${person.id}`} className="flex items-center gap-3 min-w-0">
      <Avatar name={person.full_name} src={person.avatar_url} size="sm" />
      <div className="min-w-0">
        <p className="text-sm font-medium text-ink-50 truncate">{person.full_name}</p>
        {person.roles[0] && <RoleBadge role={person.roles[0]} />}
      </div>
    </Link>
  )
}
