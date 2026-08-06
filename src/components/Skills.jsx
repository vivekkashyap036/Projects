import Section from './Section'

export default function Skills({ items }) {
  return (
    <Section title="Skills">
      <div className="flex flex-wrap gap-2">
        {items.map((skill) => (
          <span
            key={skill}
            className="text-sm px-3 py-1 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200"
          >
            {skill}
          </span>
        ))}
      </div>
    </Section>
  )
}
