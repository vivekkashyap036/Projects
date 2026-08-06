import { Mail, Phone, Link2, Printer } from 'lucide-react'

function initials(name) {
  return name
    .split(' ')
    .filter(Boolean)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export default function Header({ resume }) {
  return (
    <header className="relative overflow-hidden bg-gradient-to-br from-indigo-600 via-indigo-600 to-violet-700 dark:from-indigo-800 dark:via-indigo-800 dark:to-violet-900 px-6 sm:px-10 py-10 rounded-t-2xl">
      <div
        aria-hidden
        className="absolute -top-16 -right-16 w-56 h-56 rounded-full bg-white/10 blur-2xl"
      />
      <div
        aria-hidden
        className="absolute -bottom-20 -left-10 w-64 h-64 rounded-full bg-black/10 blur-2xl"
      />

      <button
        type="button"
        onClick={() => window.print()}
        className="no-print absolute top-5 right-5 inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full bg-white/15 text-white hover:bg-white/25 transition-colors backdrop-blur-sm"
      >
        <Printer size={14} /> Save as PDF
      </button>

      <div className="relative flex items-center gap-5">
        <div className="shrink-0 w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-white/15 backdrop-blur-sm border border-white/25 flex items-center justify-center text-white text-xl sm:text-2xl font-bold tracking-wide">
          {initials(resume.name)}
        </div>
        <div className="min-w-0">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white truncate">
            {resume.name}
          </h1>
          <p className="text-indigo-100 font-medium mt-0.5">{resume.title}</p>
        </div>
      </div>

      <div className="relative flex flex-wrap gap-2 mt-6">
        {resume.phone && (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full bg-white/10 text-indigo-50">
            <Phone size={13} /> {resume.phone}
          </span>
        )}
        {resume.email && (
          <a
            href={`mailto:${resume.email}`}
            className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full bg-white/10 text-indigo-50 hover:bg-white/20 transition-colors"
          >
            <Mail size={13} /> {resume.email}
          </a>
        )}
        {resume.links?.map((link) => (
          <a
            key={link.url}
            href={link.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full bg-white/10 text-indigo-50 hover:bg-white/20 transition-colors"
          >
            <Link2 size={13} /> {link.label}
          </a>
        ))}
      </div>
    </header>
  )
}
