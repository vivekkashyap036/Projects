import { GraduationCap } from 'lucide-react'
import Section from './Section'

export default function Education({ items }) {
  return (
    <Section title="Education" icon={GraduationCap}>
      <div className="space-y-4">
        {items.map((edu) => (
          <div key={`${edu.school}-${edu.degree}`}>
            <h3 className="text-sm font-semibold text-neutral-900 dark:text-white leading-snug">
              {edu.school}
            </h3>
            <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-0.5">
              {edu.degree}
            </p>
            <div className="flex items-center justify-between text-xs text-neutral-400 dark:text-neutral-500 mt-1">
              <span>{[edu.start, edu.end].filter(Boolean).join(' — ')}</span>
              {edu.detail && (
                <span className="font-medium text-indigo-600 dark:text-indigo-400">
                  {edu.detail}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}
