import Section from './Section'

export default function Education({ items }) {
  return (
    <Section title="Education">
      <div className="space-y-4">
        {items.map((edu) => (
          <div key={`${edu.school}-${edu.degree}`}>
            <div className="flex flex-wrap justify-between items-baseline gap-x-2">
              <h3 className="font-semibold text-neutral-900 dark:text-white">
                {edu.degree}
              </h3>
              <span className="text-sm text-neutral-500 dark:text-neutral-400 whitespace-nowrap">
                {edu.start} — {edu.end}
              </span>
            </div>
            <p className="text-sm text-neutral-600 dark:text-neutral-300">
              {edu.school}
              {edu.location ? ` · ${edu.location}` : ''}
            </p>
          </div>
        ))}
      </div>
    </Section>
  )
}
