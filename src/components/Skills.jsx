import { Code2 } from 'lucide-react'
import Section from './Section'

export default function Skills({ groups }) {
  return (
    <Section title="Skills" icon={Code2}>
      <div className="space-y-4">
        {groups.map((group) => (
          <div key={group.category}>
            <p className="text-[11px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wide mb-1.5">
              {group.category}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {group.items.map((skill) => (
                <span
                  key={skill}
                  className="text-xs font-medium px-2.5 py-1 rounded-md bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-300"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}
