import Link from 'next/link'
import { redirect } from 'next/navigation'
import { Clapperboard, Film, Search, Users } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import { ROLE_OPTIONS } from '@/lib/constants'

export const dynamic = 'force-dynamic'

export default async function Home() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (user) redirect('/discover')

  return (
    <div>
      <section className="relative overflow-hidden border-b border-ink-800">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.05]"
          style={{
            backgroundImage:
              'radial-gradient(circle at 25% 25%, white 1px, transparent 1px)',
            backgroundSize: '32px 32px',
          }}
          aria-hidden
        />
        <div className="relative max-w-5xl mx-auto px-6 py-24 sm:py-32 text-center">
          <div className="inline-flex items-center gap-2 rounded-full bg-ink-900 border border-ink-800 px-4 py-1.5 text-xs font-medium text-gold-300 mb-8">
            <Clapperboard size={13} /> Built for the film industry
          </div>
          <h1 className="font-display text-4xl sm:text-6xl font-semibold text-ink-50 leading-tight max-w-3xl mx-auto">
            The network for everyone who makes films happen
          </h1>
          <p className="mt-6 text-ink-400 text-base sm:text-lg max-w-xl mx-auto">
            From actors and directors to gaffers and light boys — build your profile,
            showcase your credits, and connect with the crew you want to work with next.
          </p>
          <div className="mt-9 flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/signup"
              className="w-full sm:w-auto inline-flex items-center justify-center rounded-lg bg-gold-500 hover:bg-gold-400 text-ink-950 font-semibold px-6 py-3 transition-colors"
            >
              Create your profile
            </Link>
            <Link
              href="/login"
              className="w-full sm:w-auto inline-flex items-center justify-center rounded-lg bg-ink-900 hover:bg-ink-800 border border-ink-700 text-ink-100 font-medium px-6 py-3 transition-colors"
            >
              Sign in
            </Link>
          </div>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="grid sm:grid-cols-3 gap-6">
          <Feature
            icon={Film}
            title="Showcase your credits"
            description="List every production you've worked on — feature films, shorts, web series, ads — with your exact role on each."
          />
          <Feature
            icon={Search}
            title="Find the right people"
            description="Search and filter by role and location to find cinematographers, editors, or crew for your next project."
          />
          <Feature
            icon={Users}
            title="Grow your network"
            description="Connect with people you've worked with, and the ones you want to work with next."
          />
        </div>
      </section>

      <section className="border-t border-ink-800">
        <div className="max-w-5xl mx-auto px-6 py-16">
          <p className="text-xs font-semibold uppercase tracking-wider text-ink-500 text-center mb-6">
            Built for every role on set
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {ROLE_OPTIONS.map((role) => (
              <span
                key={role}
                className="text-xs font-medium text-ink-300 bg-ink-900 border border-ink-800 rounded-full px-3 py-1.5"
              >
                {role}
              </span>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}

function Feature({
  icon: Icon,
  title,
  description,
}: {
  icon: typeof Film
  title: string
  description: string
}) {
  return (
    <div className="rounded-2xl bg-ink-900 border border-ink-800 p-6">
      <div className="w-10 h-10 rounded-xl bg-gold-500/10 text-gold-400 flex items-center justify-center mb-4">
        <Icon size={19} />
      </div>
      <h3 className="font-display font-semibold text-lg text-ink-50">{title}</h3>
      <p className="text-sm text-ink-400 mt-1.5 leading-relaxed">{description}</p>
    </div>
  )
}
