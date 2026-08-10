import { Link, useNavigate } from 'react-router-dom'
import { Play, Plus, Spade, Trophy } from 'lucide-react'
import { useGame } from '../hooks/useGame'

export default function Home() {
  const { game, totals } = useGame()
  const navigate = useNavigate()

  const leaderboard = game
    ? [...game.players].sort((a, b) => totals[a.id] - totals[b.id])
    : []

  return (
    <div className="space-y-8">
      <div className="text-center pt-4 pb-2">
        <div className="inline-flex w-16 h-16 rounded-2xl bg-gradient-to-br from-gold-400 to-gold-600 items-center justify-center shadow-xl shadow-black/30 mb-4">
          <Spade size={30} className="text-felt-950" strokeWidth={2.5} />
        </div>
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-white">Cabo Scorekeeper</h1>
        <p className="mt-2 text-felt-100/60 text-sm sm:text-base">
          Track every round, every peek, every failed Cabo call.
        </p>
      </div>

      {game && game.status === 'active' && (
        <div className="rounded-2xl bg-felt-900 border border-felt-800 p-5 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-felt-100/50">
              Game in progress · Round {game.rounds.length + 1}
            </p>
            <span className="text-xs text-felt-100/40">Target {game.targetScore}</span>
          </div>
          <ul className="space-y-2 mb-5">
            {leaderboard.map((p, i) => (
              <li key={p.id} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 text-felt-50">
                  <span className={`w-5 text-center text-xs ${i === 0 ? 'text-gold-400' : 'text-felt-100/30'}`}>
                    {i + 1}
                  </span>
                  {p.name}
                </span>
                <span className="font-mono font-semibold text-felt-50">{totals[p.id]}</span>
              </li>
            ))}
          </ul>
          <button
            onClick={() => navigate('/play')}
            className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-gold-500 hover:bg-gold-400 text-felt-950 font-semibold py-3 transition-colors"
          >
            <Play size={17} /> Continue Game
          </button>
        </div>
      )}

      <div className={game?.status === 'active' ? '' : 'rounded-2xl bg-felt-900 border border-felt-800 p-6 text-center'}>
        {game?.status === 'active' ? (
          <Link
            to="/new"
            className="block text-center text-sm text-felt-100/50 hover:text-felt-100/80 transition-colors"
          >
            Start a different game instead
          </Link>
        ) : (
          <>
            {game?.status === 'finished' && (
              <div className="mb-5 inline-flex items-center gap-2 text-gold-300 text-sm font-medium">
                <Trophy size={16} /> Last game finished — see History
              </div>
            )}
            <Link
              to="/new"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-gold-500 hover:bg-gold-400 text-felt-950 font-semibold px-6 py-3.5 transition-colors"
            >
              <Plus size={18} /> New Game
            </Link>
          </>
        )}
      </div>
    </div>
  )
}
