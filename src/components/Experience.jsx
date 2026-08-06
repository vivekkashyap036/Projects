import Section from './Section'

export default function Experience({ items }) {
  return (
    <Section title="Experience">
      <div className="space-y-6">
        {items.map((job) => (
          <div key={`${job.company}-${job.role}`}>
            <div className="flex flex-wrap justify-between items-baseline gap-x-2">
              <h3 className="font-semibold text-neutral-900 dark:text-white">
                {job.role} · {job.company}
              </h3>
              <span className="text-sm text-neutral-500 dark:text-neutral-400 whitespace-nowrap">
                {job.start} — {job.end}
              </span>
            </div>
            {job.location && (
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                {job.location}
              </p>
            )}
            <ul className="list-disc list-outside ml-5 mt-2 space-y-1 text-sm text-neutral-700 dark:text-neutral-300">
              {job.bullets.map((bullet, i) => (
                <li key={i}>{bullet}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Section>
  )
}
