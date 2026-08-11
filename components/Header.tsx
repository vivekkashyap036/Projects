import Link from 'next/link'
import { Clapperboard, LogOut, Search, User, Users } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'

export default async function Header() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  return (
    <header className="sticky top-0 z-40 bg-ink-950/90 backdrop-blur border-b border-ink-800">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <Link href={user ? '/discover' : '/'} className="flex items-center gap-2">
          <Clapperboard size={20} className="text-gold-400" />
          <span className="font-display text-lg font-semibold text-ink-50">Callsheet</span>
        </Link>

        {user ? (
          <nav className="flex items-center gap-1">
            <Link
              href="/discover"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-ink-300 hover:text-ink-50 hover:bg-white/5 transition-colors"
            >
              <Search size={15} />
              <span className="hidden sm:inline">Discover</span>
            </Link>
            <Link
              href="/connections"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-ink-300 hover:text-ink-50 hover:bg-white/5 transition-colors"
            >
              <Users size={15} />
              <span className="hidden sm:inline">Connections</span>
            </Link>
            <Link
              href={`/profile/${user.id}`}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-ink-300 hover:text-ink-50 hover:bg-white/5 transition-colors"
            >
              <User size={15} />
              <span className="hidden sm:inline">Profile</span>
            </Link>
            <form action="/auth/signout" method="post">
              <button
                type="submit"
                aria-label="Sign out"
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-ink-400 hover:text-red-400 hover:bg-white/5 transition-colors"
              >
                <LogOut size={15} />
              </button>
            </form>
          </nav>
        ) : (
          <nav className="flex items-center gap-2">
            <Link
              href="/login"
              className="px-3 py-2 rounded-lg text-sm font-medium text-ink-300 hover:text-ink-50 transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/signup"
              className="px-3.5 py-2 rounded-lg text-sm font-semibold bg-gold-500 hover:bg-gold-400 text-ink-950 transition-colors"
            >
              Join
            </Link>
          </nav>
        )}
      </div>
    </header>
  )
}
