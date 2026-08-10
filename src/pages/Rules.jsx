import { ScrollText } from 'lucide-react'
import { rulesSections } from '../lib/rulesContent'

export default function Rules() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-white inline-flex items-center gap-2.5">
          <ScrollText size={22} className="text-gold-400" /> How to Play Cabo
        </h1>
        <p className="text-sm text-felt-100/50 mt-1">
          The most common ruleset. If your table plays differently, that's the house rules —
          the scorekeeper still works the same way.
        </p>
      </div>

      <div className="space-y-4">
        {rulesSections.map((section, i) => (
          <div key={section.title} className="rounded-2xl bg-felt-900 border border-felt-800 p-5 sm:p-6">
            <div className="flex items-baseline gap-3 mb-2">
              <span className="font-mono text-xs text-gold-500/70">{String(i + 1).padStart(2, '0')}</span>
              <h2 className="font-display text-lg font-semibold text-white">{section.title}</h2>
            </div>
            <p className="text-sm text-felt-100/70 leading-relaxed">{section.body}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
