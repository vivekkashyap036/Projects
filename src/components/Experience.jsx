import { Briefcase } from 'lucide-react'
import Section from './Section'

export default function Experience({ items }) {
  return (
    <Section title="Experience" icon={Briefcase}>
      <div className="relative border-l-2 border-indigo-100 dark:border-indigo-900/60 ml-1 space-y-7">
        {items.map((job) => (
          <div key={`${job.company}-${job.role}-${job.start}`} className="relative pl-6">
            <span className="absolute -left-[7px] top-1.5 w-3 h-3 rounded-full bg-indigo-500 ring-4 ring-white dark:ring-neutral-900" />

            <div className="flex flex-wrap justify-between items-baseline gap-x-3 gap-y-0.5">
              <h3 className="font-semibold text-neutral-900 dark:text-white">
                {job.role}
                <span className="font-normal text-neutral-500 dark:text-neutral-400">
                  {' '}
                  · {job.company}
                </span>
              </h3>
              <span className="text-xs font-medium text-indigo-600 dark:text-indigo-400 whitespace-nowrap">
                {job.start} — {job.end}
              </span>
            </div>
            {job.location && (
              <p className="text-xs text-neutral-400 dark:text-neutral-500 mt-0.5">
                {job.location}
              </p>
            )}
            <ul className="mt-2.5 space-y-1.5 text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">
              {job.bullets.map((bullet, i) => (
                <li key={i} className="relative pl-4">
                  <span className="absolute left-0 top-[0.6em] w-1.5 h-1.5 rounded-full bg-neutral-300 dark:bg-neutral-600" />
                  {bullet}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Section>
  )
}
