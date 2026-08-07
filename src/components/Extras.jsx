import { Globe2, Heart } from 'lucide-react'
import Section from './Section'

export function Languages({ items }) {
  if (!items?.length) return null
  return (
    <Section title="Languages" icon={Globe2}>
      <div className="flex flex-wrap gap-1.5">
        {items.map((lang) => (
          <span
            key={lang}
            className="text-xs font-medium px-2.5 py-1 rounded-md bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300"
          >
            {lang}
          </span>
        ))}
      </div>
    </Section>
  )
}

export function Extracurricular({ items }) {
  if (!items?.length) return null
  return (
    <Section title="Extracurricular" icon={Heart}>
      <ul className="space-y-2 text-sm text-neutral-700 dark:text-neutral-300">
        {items.map((item) => (
          <li key={item} className="relative pl-4">
            <span className="absolute left-0 top-[0.6em] w-1.5 h-1.5 rounded-full bg-neutral-300 dark:bg-neutral-600" />
            {item}
          </li>
        ))}
      </ul>
    </Section>
  )
}
