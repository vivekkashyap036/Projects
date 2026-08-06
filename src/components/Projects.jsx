import Section from './Section'

export default function Projects({ items }) {
  if (!items?.length) return null

  return (
    <Section title="Projects">
      <div className="space-y-4">
        {items.map((project) => (
          <div key={project.name}>
            <h3 className="font-semibold text-neutral-900 dark:text-white">
              {project.url ? (
                <a
                  href={project.url}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:underline"
                >
                  {project.name}
                </a>
              ) : (
                project.name
              )}
            </h3>
            <p className="text-sm text-neutral-700 dark:text-neutral-300">
              {project.description}
            </p>
          </div>
        ))}
      </div>
    </Section>
  )
}
