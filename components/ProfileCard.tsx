import Link from 'next/link'
import { MapPin } from 'lucide-react'
import Avatar from './Avatar'
import RoleBadge from './RoleBadge'
import type { Profile } from '@/lib/types'

export default function ProfileCard({ profile }: { profile: Profile }) {
  return (
    <Link
      href={`/profile/${profile.id}`}
      className="block bg-ink-900 border border-ink-800 rounded-2xl p-5 hover:border-gold-500/40 transition-colors"
    >
      <div className="flex items-start gap-3">
        <Avatar name={profile.full_name} src={profile.avatar_url} />
        <div className="min-w-0">
          <p className="font-semibold text-ink-50 truncate">{profile.full_name}</p>
          {profile.headline && (
            <p className="text-sm text-ink-400 truncate">{profile.headline}</p>
          )}
          {profile.location && (
            <p className="inline-flex items-center gap-1 text-xs text-ink-500 mt-0.5">
              <MapPin size={11} /> {profile.location}
            </p>
          )}
        </div>
      </div>

      {profile.roles.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-4">
          {profile.roles.slice(0, 4).map((role) => (
            <RoleBadge key={role} role={role} />
          ))}
          {profile.roles.length > 4 && (
            <span className="text-[11px] text-ink-500 px-1 py-0.5">
              +{profile.roles.length - 4} more
            </span>
          )}
        </div>
      )}
    </Link>
  )
}
