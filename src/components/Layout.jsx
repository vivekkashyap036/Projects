import { Link, useLocation } from 'react-router-dom'
import { Club, Diamond, Heart, ScrollText, Spade, History as HistoryIcon, Play } from 'lucide-react'

const navLinks = [
  { to: '/', label: 'Play', icon: Play },
  { to: '/rules', label: 'Rules', icon: ScrollText },
  { to: '/history', label: 'History', icon: HistoryIcon },
]

export default function Layout({ children }) {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-felt-950 text-felt-50 flex flex-col">
      <div
        className="pointer-events-none fixed inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            'radial-gradient(circle at 20% 20%, white 1px, transparent 1px), radial-gradient(circle at 60% 70%, white 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
        aria-hidden
      />

      <header className="relative border-b border-felt-800/80 bg-felt-900/60 backdrop-blur">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 group">
            <span className="relative w-9 h-9 rounded-lg bg-gradient-to-br from-gold-400 to-gold-600 flex items-center justify-center shadow-lg shadow-black/20">
              <Spade size={18} className="text-felt-950" strokeWidth={2.5} />
            </span>
            <span className="font-display font-bold text-xl tracking-wide text-gold-300">
              Cabo
            </span>
          </Link>

          <nav className="flex items-center gap-1">
            {navLinks.map((link) => {
              const active = location.pathname === link.to
              const Icon = link.icon
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    active
                      ? 'bg-gold-400/15 text-gold-300'
                      : 'text-felt-100/70 hover:text-felt-50 hover:bg-white/5'
                  }`}
                >
                  <Icon size={15} />
                  <span className="hidden sm:inline">{link.label}</span>
                </Link>
              )
            })}
          </nav>
        </div>
      </header>

      <main className="relative flex-1 max-w-2xl w-full mx-auto px-4 sm:px-6 py-8">
        {children}
      </main>

      <footer className="relative border-t border-felt-800/80 py-4">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 flex items-center justify-center gap-3 text-felt-100/30">
          <Spade size={13} />
          <Heart size={13} />
          <Club size={13} />
          <Diamond size={13} />
        </div>
      </footer>
    </div>
  )
}
