import { redirect } from 'next/navigation'
import { Clapperboard } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import { createProfile } from '@/app/actions'
import RoleCheckboxes from '@/components/RoleCheckboxes'

export const dynamic = 'force-dynamic'

export default async function OnboardingPage() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const { data: existing } = await supabase
    .from('profiles')
    .select('id')
    .eq('id', user.id)
    .maybeSingle()
  if (existing) redirect('/discover')

  return (
    <div className="max-w-xl mx-auto px-6 py-12">
      <div className="text-center mb-8">
        <Clapperboard size={26} className="text-gold-400 mx-auto mb-3" />
        <h1 className="font-display text-2xl font-semibold text-ink-50">
          Set up your profile
        </h1>
        <p className="text-sm text-ink-400 mt-1">
          This is what people will see when they find you.
        </p>
      </div>

      <form action={createProfile} className="space-y-6">
        <div>
          <label htmlFor="avatar" className="block text-xs font-medium text-ink-300 mb-1.5">
            Photo
          </label>
          <input
            id="avatar"
            name="avatar"
            type="file"
            accept="image/*"
            className="block w-full text-sm text-ink-400 file:mr-3 file:rounded-lg file:border-0 file:bg-ink-800 file:text-ink-200 file:px-3 file:py-2 file:text-sm file:font-medium hover:file:bg-ink-700"
          />
        </div>

        <div>
          <label htmlFor="full_name" className="block text-xs font-medium text-ink-300 mb-1.5">
            Full name
          </label>
          <input
            id="full_name"
            name="full_name"
            required
            className="w-full rounded-lg bg-ink-900 border border-ink-700 px-3.5 py-2.5 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500"
          />
        </div>

        <div>
          <label htmlFor="headline" className="block text-xs font-medium text-ink-300 mb-1.5">
            Headline
          </label>
          <input
            id="headline"
            name="headline"
            placeholder="e.g. Cinematographer based in Mumbai"
            className="w-full rounded-lg bg-ink-900 border border-ink-700 px-3.5 py-2.5 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500"
          />
        </div>

        <div>
          <label htmlFor="location" className="block text-xs font-medium text-ink-300 mb-1.5">
            Location
          </label>
          <input
            id="location"
            name="location"
            placeholder="City, Country"
            className="w-full rounded-lg bg-ink-900 border border-ink-700 px-3.5 py-2.5 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500"
          />
        </div>

        <div>
          <p className="block text-xs font-medium text-ink-300 mb-1.5">
            What do you do? <span className="text-ink-500">(select all that apply)</span>
          </p>
          <RoleCheckboxes />
        </div>

        <div>
          <label htmlFor="bio" className="block text-xs font-medium text-ink-300 mb-1.5">
            Bio
          </label>
          <textarea
            id="bio"
            name="bio"
            rows={4}
            placeholder="A short introduction — your experience, style, what you're looking for."
            className="w-full rounded-lg bg-ink-900 border border-ink-700 px-3.5 py-2.5 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500"
          />
        </div>

        <button
          type="submit"
          className="w-full rounded-lg bg-gold-500 hover:bg-gold-400 text-ink-950 font-semibold py-3 text-sm transition-colors"
        >
          Create profile
        </button>
      </form>
    </div>
  )
}
