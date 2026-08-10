import { useState } from 'react'
import { Plus, Spade } from 'lucide-react'

export default function RoundForm({ players, onSubmit }) {
  const [scores, setScores] = useState(() => Object.fromEntries(players.map((p) => [p.id, ''])))
  const [caboCallerId, setCaboCallerId] = useState(null)

  const allFilled = players.every((p) => scores[p.id] !== '' && !Number.isNaN(Number(scores[p.id])))

  function setScore(id, value) {
    if (value !== '' && !/^\d{0,3}$/.test(value)) return
    setScores((prev) => ({ ...prev, [id]: value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!allFilled) return
    const rawScores = Object.fromEntries(players.map((p) => [p.id, Number(scores[p.id])]))
    onSubmit(rawScores, caboCallerId)
    setScores(Object.fromEntries(players.map((p) => [p.id, ''])))
    setCaboCallerId(null)
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-2xl bg-felt-900 border border-felt-800 p-5 sm:p-6 space-y-5">
      <p className="text-xs font-semibold uppercase tracking-wider text-felt-100/50">
        Enter hand totals for this round
      </p>

      <div className="space-y-2.5">
        {players.map((p) => (
          <div key={p.id} className="flex items-center gap-3">
            <label htmlFor={`score-${p.id}`} className="flex-1 text-sm text-felt-50 truncate">
              {p.name}
            </label>
            <input
              id={`score-${p.id}`}
              inputMode="numeric"
              value={scores[p.id]}
              onChange={(e) => setScore(p.id, e.target.value)}
              placeholder="0"
              className="w-16 text-center rounded-lg bg-felt-950 border border-felt-800 px-2 py-2 text-sm font-mono text-white placeholder:text-felt-100/30 focus:outline-none focus:ring-2 focus:ring-gold-500"
            />
          </div>
        ))}
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-felt-100/50 mb-2">
          Who called Cabo?
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setCaboCallerId(null)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
              caboCallerId === null
                ? 'bg-felt-100/10 border-felt-100/30 text-felt-50'
                : 'border-felt-800 text-felt-100/50 hover:text-felt-100/80'
            }`}
          >
            No one
          </button>
          {players.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setCaboCallerId(p.id)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                caboCallerId === p.id
                  ? 'bg-gold-400/15 border-gold-500/60 text-gold-300'
                  : 'border-felt-800 text-felt-100/50 hover:text-felt-100/80'
              }`}
            >
              <Spade size={11} /> {p.name}
            </button>
          ))}
        </div>
      </div>

      <button
        type="submit"
        disabled={!allFilled}
        className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-gold-500 hover:bg-gold-400 disabled:bg-felt-800 disabled:text-felt-100/30 text-felt-950 font-semibold py-3 transition-colors"
      >
        <Plus size={16} /> Add Round
      </button>
    </form>
  )
}
