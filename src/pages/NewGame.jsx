import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Minus, Plus, Users, X } from 'lucide-react'
import { useGame } from '../hooks/useGame'
import { newPlayerId, DEFAULT_TARGET_SCORE, DEFAULT_CABO_PENALTY } from '../lib/gameLogic'

export default function NewGame() {
  const { startGame } = useGame()
  const navigate = useNavigate()
  const [players, setPlayers] = useState([
    { id: newPlayerId(), name: '' },
    { id: newPlayerId(), name: '' },
  ])
  const [targetScore, setTargetScore] = useState(DEFAULT_TARGET_SCORE)
  const [penalty, setPenalty] = useState(DEFAULT_CABO_PENALTY)

  function updateName(id, name) {
    setPlayers((prev) => prev.map((p) => (p.id === id ? { ...p, name } : p)))
  }

  function addPlayer() {
    setPlayers((prev) => [...prev, { id: newPlayerId(), name: '' }])
  }

  function removePlayer(id) {
    setPlayers((prev) => prev.filter((p) => p.id !== id))
  }

  const readyPlayers = players
    .map((p) => ({ ...p, name: p.name.trim() }))
    .filter((p) => p.name.length > 0)
  const canStart = readyPlayers.length >= 2

  function handleStart(e) {
    e.preventDefault()
    if (!canStart) return
    startGame(readyPlayers, Number(targetScore), Number(penalty))
    navigate('/play')
  }

  return (
    <form onSubmit={handleStart} className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-white">New Game</h1>
        <p className="text-sm text-felt-100/50 mt-1">Add everyone at the table.</p>
      </div>

      <div className="rounded-2xl bg-felt-900 border border-felt-800 p-5 sm:p-6 space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-felt-100/50 inline-flex items-center gap-1.5 mb-1">
          <Users size={13} /> Players
        </p>
        {players.map((player, i) => (
          <div key={player.id} className="flex items-center gap-2">
            <input
              value={player.name}
              onChange={(e) => updateName(player.id, e.target.value)}
              placeholder={`Player ${i + 1}`}
              className="flex-1 rounded-lg bg-felt-950 border border-felt-800 px-3.5 py-2.5 text-sm text-white placeholder:text-felt-100/30 focus:outline-none focus:ring-2 focus:ring-gold-500"
            />
            {players.length > 2 && (
              <button
                type="button"
                onClick={() => removePlayer(player.id)}
                aria-label={`Remove player ${i + 1}`}
                className="p-2 text-felt-100/40 hover:text-red-400 transition-colors"
              >
                <X size={16} />
              </button>
            )}
          </div>
        ))}
        <button
          type="button"
          onClick={addPlayer}
          className="w-full inline-flex items-center justify-center gap-1.5 rounded-lg border border-dashed border-felt-700 text-felt-100/60 hover:text-felt-50 hover:border-felt-500 text-sm font-medium py-2.5 transition-colors"
        >
          <Plus size={15} /> Add player
        </button>
      </div>

      <div className="rounded-2xl bg-felt-900 border border-felt-800 p-5 sm:p-6 space-y-5">
        <NumberField
          label="Target score"
          hint="Game ends once anyone reaches this total."
          value={targetScore}
          onChange={setTargetScore}
          step={10}
          min={20}
        />
        <NumberField
          label="Failed Cabo penalty"
          hint="Added to a caller's hand if they weren't strictly lowest."
          value={penalty}
          onChange={setPenalty}
          step={1}
          min={0}
        />
      </div>

      <button
        type="submit"
        disabled={!canStart}
        className="w-full inline-flex items-center justify-center rounded-xl bg-gold-500 hover:bg-gold-400 disabled:bg-felt-800 disabled:text-felt-100/30 text-felt-950 font-semibold py-3.5 transition-colors"
      >
        {canStart ? 'Start Game' : 'Add at least 2 players'}
      </button>
    </form>
  )
}

function NumberField({ label, hint, value, onChange, step, min }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-felt-50">{label}</p>
        <p className="text-xs text-felt-100/40 mt-0.5">{hint}</p>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        <button
          type="button"
          onClick={() => onChange(Math.max(min, Number(value) - step))}
          className="w-8 h-8 rounded-lg bg-felt-950 border border-felt-800 flex items-center justify-center text-felt-100/60 hover:text-white transition-colors"
        >
          <Minus size={14} />
        </button>
        <span className="w-12 text-center font-mono text-white">{value}</span>
        <button
          type="button"
          onClick={() => onChange(Number(value) + step)}
          className="w-8 h-8 rounded-lg bg-felt-950 border border-felt-800 flex items-center justify-center text-felt-100/60 hover:text-white transition-colors"
        >
          <Plus size={14} />
        </button>
      </div>
    </div>
  )
}
