'use client'

import { useState, type FormEvent } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Clapperboard } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const supabase = createClient()
    const { error } = await supabase.auth.signInWithPassword({ email, password })

    if (error) {
      setError(error.message)
      setLoading(false)
      return
    }

    router.replace('/discover')
    router.refresh()
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 mb-6">
            <Clapperboard size={22} className="text-gold-400" />
            <span className="font-display text-xl font-semibold text-ink-50">Callsheet</span>
          </Link>
          <h1 className="font-display text-2xl font-semibold text-ink-50">Welcome back</h1>
          <p className="text-sm text-ink-400 mt-1">Sign in to your profile</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-xs font-medium text-ink-300 mb-1.5">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg bg-ink-900 border border-ink-700 px-3.5 py-2.5 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-xs font-medium text-ink-300 mb-1.5">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg bg-ink-900 border border-ink-700 px-3.5 py-2.5 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500"
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-gold-500 hover:bg-gold-400 disabled:opacity-60 text-ink-950 font-semibold py-2.5 text-sm transition-colors"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="text-center text-sm text-ink-400 mt-6">
          New here?{' '}
          <Link href="/signup" className="text-gold-400 hover:text-gold-300 font-medium">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  )
}
