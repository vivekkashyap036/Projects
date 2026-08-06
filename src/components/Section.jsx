export default function Section({ title, children }) {
  return (
    <section className="mb-8">
      <h2 className="text-sm font-semibold tracking-widest uppercase text-neutral-500 dark:text-neutral-400 border-b border-neutral-200 dark:border-neutral-700 pb-2 mb-4">
        {title}
      </h2>
      {children}
    </section>
  )
}
