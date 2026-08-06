export default function Section({ title, icon: Icon, children, className = '' }) {
  return (
    <section className={className}>
      <div className="flex items-center gap-2 mb-4">
        {Icon && <Icon size={16} className="text-indigo-600 dark:text-indigo-400" strokeWidth={2.25} />}
        <h2 className="text-xs font-bold tracking-[0.14em] uppercase text-neutral-500 dark:text-neutral-400">
          {title}
        </h2>
      </div>
      {children}
    </section>
  )
}
