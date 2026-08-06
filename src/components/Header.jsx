import { Mail, MapPin, Phone } from 'lucide-react'

export default function Header({ resume }) {
  return (
    <header className="mb-8 text-center sm:text-left">
      <h1 className="text-3xl sm:text-4xl font-bold text-neutral-900 dark:text-white">
        {resume.name}
      </h1>
      <p className="text-lg text-neutral-600 dark:text-neutral-300 mt-1">
        {resume.title}
      </p>

      <div className="flex flex-wrap justify-center sm:justify-start gap-x-4 gap-y-1 mt-3 text-sm text-neutral-500 dark:text-neutral-400">
        {resume.location && (
          <span className="inline-flex items-center gap-1">
            <MapPin size={14} /> {resume.location}
          </span>
        )}
        {resume.email && (
          <a
            href={`mailto:${resume.email}`}
            className="inline-flex items-center gap-1 hover:text-neutral-900 dark:hover:text-white"
          >
            <Mail size={14} /> {resume.email}
          </a>
        )}
        {resume.phone && (
          <span className="inline-flex items-center gap-1">
            <Phone size={14} /> {resume.phone}
          </span>
        )}
      </div>

      {resume.links?.length > 0 && (
        <div className="flex flex-wrap justify-center sm:justify-start gap-x-4 gap-y-1 mt-2 text-sm">
          {resume.links.map((link) => (
            <a
              key={link.url}
              href={link.url}
              target="_blank"
              rel="noreferrer"
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              {link.label}
            </a>
          ))}
        </div>
      )}
    </header>
  )
}
