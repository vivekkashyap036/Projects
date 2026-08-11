export default function RoleBadge({ role, size = 'sm' }: { role: string; size?: 'sm' | 'md' }) {
  return (
    <span
      className={`inline-flex items-center rounded-full bg-gold-500/10 text-gold-300 border border-gold-500/20 font-medium ${
        size === 'sm' ? 'text-[11px] px-2 py-0.5' : 'text-xs px-2.5 py-1'
      }`}
    >
      {role}
    </span>
  )
}
