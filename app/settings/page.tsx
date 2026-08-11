import { redirect } from 'next/navigation'
import { Trash2 } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import { addCredit, deleteCredit, updateProfile } from '@/app/actions'
import RoleCheckboxes from '@/components/RoleCheckboxes'
import Avatar from '@/components/Avatar'
import { PROJECT_TYPES } from '@/lib/constants'
import type { Credit, Profile } from '@/lib/types'

export const dynamic = 'force-dynamic'

export default async function SettingsPage() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const [{ data: profile }, { data: credits }] = await Promise.all([
    supabase.from('profiles').select('*').eq('id', user.id).maybeSingle<Profile>(),
    supabase
      .from('credits')
      .select('*')
      .eq('profile_id', user.id)
      .order('project_year', { ascending: false })
      .returns<Credit[]>(),
  ])

  if (!profile) redirect('/onboarding')

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10 space-y-10">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink-50">Edit profile</h1>
        <p className="text-sm text-ink-400 mt-1">Keep your profile current.</p>
      </div>

      <form action={updateProfile} className="space-y-6">
        <div className="flex items-center gap-4">
          <Avatar name={profile.full_name} src={profile.avatar_url} size="md" />
          <div className="flex-1">
            <label htmlFor="avatar" className="block text-xs font-medium text-ink-300 mb-1.5">
              Replace photo
            </label>
            <input
              id="avatar"
              name="avatar"
              type="file"
              accept="image/*"
              className="block w-full text-sm text-ink-400 file:mr-3 file:rounded-lg file:border-0 file:bg-ink-800 file:text-ink-200 file:px-3 file:py-2 file:text-sm file:font-medium hover:file:bg-ink-700"
            />
          </div>
        </div>

        <div>
          <label htmlFor="full_name" className="block text-xs font-medium text-ink-300 mb-1.5">
            Full name
          </label>
          <input
            id="full_name"
            name="full_name"
            required
            defaultValue={profile.full_name}
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
            defaultValue={profile.headline ?? ''}
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
            defaultValue={profile.location ?? ''}
            className="w-full rounded-lg bg-ink-900 border border-ink-700 px-3.5 py-2.5 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500"
          />
        </div>

        <div>
          <p className="block text-xs font-medium text-ink-300 mb-1.5">What do you do?</p>
          <RoleCheckboxes selected={profile.roles} />
        </div>

        <div>
          <label htmlFor="bio" className="block text-xs font-medium text-ink-300 mb-1.5">
            Bio
          </label>
          <textarea
            id="bio"
            name="bio"
            rows={4}
            defaultValue={profile.bio ?? ''}
            className="w-full rounded-lg bg-ink-900 border border-ink-700 px-3.5 py-2.5 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500"
          />
        </div>

        <button
          type="submit"
          className="rounded-lg bg-gold-500 hover:bg-gold-400 text-ink-950 font-semibold px-5 py-2.5 text-sm transition-colors"
        >
          Save changes
        </button>
      </form>

      <div className="border-t border-ink-800 pt-8">
        <h2 className="font-display text-lg font-semibold text-ink-50 mb-1">Filmography</h2>
        <p className="text-sm text-ink-400 mb-5">Add every production you&apos;ve worked on.</p>

        <div className="space-y-2 mb-6">
          {credits?.map((credit) => (
            <div
              key={credit.id}
              className="flex items-center justify-between gap-4 bg-ink-900 border border-ink-800 rounded-xl px-4 py-3"
            >
              <div className="min-w-0">
                <p className="font-medium text-ink-50 truncate">{credit.project_title}</p>
                <p className="text-xs text-ink-400 mt-0.5">
                  {credit.role_on_project}
                  {credit.project_type ? ` · ${credit.project_type}` : ''}
                  {credit.project_year ? ` · ${credit.project_year}` : ''}
                </p>
              </div>
              <form action={deleteCredit.bind(null, credit.id)}>
                <button
                  type="submit"
                  aria-label="Delete credit"
                  className="text-ink-500 hover:text-red-400 transition-colors p-1"
                >
                  <Trash2 size={15} />
                </button>
              </form>
            </div>
          ))}
        </div>

        <form action={addCredit} className="grid sm:grid-cols-2 gap-3 bg-ink-900 border border-ink-800 rounded-xl p-4">
          <input
            name="project_title"
            required
            placeholder="Project title"
            className="rounded-lg bg-ink-950 border border-ink-700 px-3 py-2 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500 sm:col-span-2"
          />
          <input
            name="role_on_project"
            required
            placeholder="Your role (e.g. Lead Actor, Gaffer)"
            className="rounded-lg bg-ink-950 border border-ink-700 px-3 py-2 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500"
          />
          <select
            name="project_type"
            defaultValue=""
            className="rounded-lg bg-ink-950 border border-ink-700 px-3 py-2 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500"
          >
            <option value="">Project type</option>
            {PROJECT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <input
            name="project_year"
            type="number"
            placeholder="Year"
            min={1900}
            max={2100}
            className="rounded-lg bg-ink-950 border border-ink-700 px-3 py-2 text-sm text-ink-50 focus:outline-none focus:ring-2 focus:ring-gold-500"
          />
          <button
            type="submit"
            className="rounded-lg bg-ink-800 hover:bg-ink-700 text-ink-100 text-sm font-medium py-2 transition-colors"
          >
            Add credit
          </button>
        </form>
      </div>
    </div>
  )
}
