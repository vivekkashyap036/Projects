'use client'

import { useTransition } from 'react'
import { Check, UserPlus, X } from 'lucide-react'
import {
  removeConnection,
  respondToConnection,
  sendConnectionRequest,
} from '@/app/actions'
import type { Connection } from '@/lib/types'

export default function ConnectButton({
  profileId,
  currentUserId,
  connection,
}: {
  profileId: string
  currentUserId: string
  connection: Connection | null
}) {
  const [isPending, startTransition] = useTransition()

  if (profileId === currentUserId) return null

  if (!connection) {
    return (
      <button
        disabled={isPending}
        onClick={() => startTransition(() => sendConnectionRequest(profileId))}
        className="inline-flex items-center gap-1.5 rounded-lg bg-gold-500 hover:bg-gold-400 disabled:opacity-60 text-ink-950 font-semibold text-sm px-4 py-2 transition-colors"
      >
        <UserPlus size={15} /> Connect
      </button>
    )
  }

  if (connection.status === 'accepted') {
    return (
      <div className="inline-flex items-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-lg bg-ink-800 text-ink-200 text-sm font-medium px-4 py-2">
          <Check size={15} className="text-gold-400" /> Connected
        </span>
        <button
          disabled={isPending}
          onClick={() => startTransition(() => removeConnection(connection.id))}
          className="text-xs text-ink-500 hover:text-red-400 transition-colors"
        >
          Remove
        </button>
      </div>
    )
  }

  // status === 'pending'
  if (connection.requester_id === currentUserId) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-lg bg-ink-800 text-ink-400 text-sm font-medium px-4 py-2">
        Request sent
      </span>
    )
  }

  return (
    <div className="inline-flex items-center gap-2">
      <button
        disabled={isPending}
        onClick={() => startTransition(() => respondToConnection(connection.id, true))}
        className="inline-flex items-center gap-1.5 rounded-lg bg-gold-500 hover:bg-gold-400 disabled:opacity-60 text-ink-950 font-semibold text-sm px-4 py-2 transition-colors"
      >
        <Check size={15} /> Accept
      </button>
      <button
        disabled={isPending}
        onClick={() => startTransition(() => respondToConnection(connection.id, false))}
        className="inline-flex items-center gap-1.5 rounded-lg bg-ink-800 hover:bg-ink-700 disabled:opacity-60 text-ink-300 text-sm px-4 py-2 transition-colors"
      >
        <X size={15} /> Decline
      </button>
    </div>
  )
}
