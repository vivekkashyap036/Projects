'use client'

import { useState, type FormEvent } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Clapperboard } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'

export default function SignupPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [checkEmail, setCheckEmail] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const supabase = createClient()
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
    })

    if (error) {
      setError(error.message)
      setLoading(false)
      return
    }

    if (data.session) {
      router.replace('/onboarding')
      router.refresh()
      return
    }

    // Email confirmation is required before a session exists.
    setCheckEmail(true)
    setLoading(false)
  }

  if (checkEmail) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 text-center">
        <div className="max-w-sm">
          <Clapperboard size={28} className="text-gold-400 mx-auto mb-4" />
          <h1 className="font-display text-xl font-semibold text-ink-50">Check your inbox</h1>
          <p className="text-sm text-ink-400 mt-2">
            We sent a confirmation link to <span className="text-ink-200">{email}</span>. Click
            it to finish creating your account.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 mb-6">
            <Clapperboard size={22} className="text-gold-400" />
            <span className="font-display text-xl font-semibold text-ink-50">Callsheet</span>
          </Link>
          <h1 className="font-display text-2xl font-semibold text-ink-50">Create your profile</h1>
          <p className="text-sm text-ink-400 mt-1">Join the crew and cast directory</p>
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
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg bg-ink-900 border border-ink-700 px-3.5 py-2.5 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500"
            />
            <p className="text-xs text-ink-500 mt-1">At least 6 characters.</p>
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-gold-500 hover:bg-gold-400 disabled:opacity-60 text-ink-950 font-semibold py-2.5 text-sm transition-colors"
          >
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="text-center text-sm text-ink-400 mt-6">
          Already have an account?{' '}
          <Link href="/login" className="text-gold-400 hover:text-gold-300 font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
