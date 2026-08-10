import { Navigate, Link } from 'react-router-dom'
import { Crown, Plus, Trophy, Undo2 } from 'lucide-react'
import { useGame } from '../hooks/useGame'
import RoundForm from '../components/RoundForm'
import ScoreTable from '../components/ScoreTable'

export default function Play() {
  const { game, totals, addRound, undoLastRound } = useGame()

  if (!game) return <Navigate to="/new" replace />

  const isFinished = game.status === 'finished'
  const winners = isFinished ? game.players.filter((p) => game.winnerIds.includes(p.id)) : []

  return (
    <div className="space-y-6">
      {isFinished && (
        <div className="rounded-2xl bg-gradient-to-br from-gold-500/20 to-gold-600/5 border border-gold-500/40 p-6 text-center">
          <Trophy size={32} className="mx-auto text-gold-400 mb-3" />
          <p className="text-xs font-semibold uppercase tracking-wider text-gold-300/80 mb-1">
            Game Over
          </p>
          <h2 className="font-display text-2xl font-bold text-white">
            {winners.map((w) => w.name).join(' & ')} {winners.length > 1 ? 'win' : 'wins'}!
          </h2>
          <p className="text-sm text-felt-100/50 mt-1">
            Final score: {totals[winners[0].id]} points
          </p>
          <Link
            to="/new"
            className="inline-flex items-center gap-2 mt-5 rounded-xl bg-gold-500 hover:bg-gold-400 text-felt-950 font-semibold px-5 py-2.5 text-sm transition-colors"
          >
            <Plus size={15} /> New Game
          </Link>
        </div>
      )}

      {!isFinished && (
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-xl font-bold text-white">
              Round {game.rounds.length + 1}
            </h1>
            <p className="text-xs text-felt-100/40 mt-0.5">Target score: {game.targetScore}</p>
          </div>
          {game.rounds.length > 0 && (
            <button
              onClick={undoLastRound}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-felt-100/50 hover:text-felt-100/80 transition-colors"
            >
              <Undo2 size={14} /> Undo last round
            </button>
          )}
        </div>
      )}

      {!isFinished && <RoundForm players={game.players} onSubmit={addRound} />}

      {isFinished && (
        <p className="text-xs font-semibold uppercase tracking-wider text-felt-100/40 inline-flex items-center gap-1.5">
          <Crown size={13} /> Final standings
        </p>
      )}

      <ScoreTable players={game.players} rounds={game.rounds} totals={totals} />
    </div>
  )
}
