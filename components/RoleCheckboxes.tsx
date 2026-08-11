import { ROLE_OPTIONS } from '@/lib/constants'

export default function RoleCheckboxes({ selected = [] }: { selected?: string[] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      {ROLE_OPTIONS.map((role) => (
        <label
          key={role}
          className="flex items-center gap-2 text-sm text-ink-200 bg-ink-900 border border-ink-700 rounded-lg px-3 py-2 cursor-pointer has-[:checked]:border-gold-500 has-[:checked]:bg-gold-500/10 has-[:checked]:text-gold-300 transition-colors"
        >
          <input
            type="checkbox"
            name="roles"
            value={role}
            defaultChecked={selected.includes(role)}
            className="accent-gold-500"
          />
          {role}
        </label>
      ))}
    </div>
  )
}
