function initials(name: string) {
  return name
    .split(' ')
    .filter(Boolean)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

const SIZES = {
  sm: 'w-9 h-9 text-xs',
  md: 'w-14 h-14 text-lg',
  lg: 'w-28 h-28 text-3xl',
}

export default function Avatar({
  name,
  src,
  size = 'md',
}: {
  name: string
  src?: string | null
  size?: keyof typeof SIZES
}) {
  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- Supabase Storage URLs vary per project, so next/image remotePatterns can't be preconfigured
      <img
        src={src}
        alt={name}
        className={`${SIZES[size]} rounded-full object-cover border border-ink-700`}
      />
    )
  }

  return (
    <div
      className={`${SIZES[size]} rounded-full bg-gradient-to-br from-gold-500 to-gold-600 text-ink-950 font-semibold flex items-center justify-center shrink-0`}
    >
      {initials(name)}
    </div>
  )
}
