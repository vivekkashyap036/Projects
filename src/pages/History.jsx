import { useState } from 'react'
import { History as HistoryIcon, Trophy } from 'lucide-react'
import { loadHistory } from '../lib/storage'

export default function History() {
  const [history] = useState(() => loadHistory())

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-white inline-flex items-center gap-2.5">
          <HistoryIcon size={22} className="text-gold-400" /> Past Games
        </h1>
        <p className="text-sm text-felt-100/50 mt-1">Every finished game, saved on this device.</p>
      </div>

      {history.length === 0 ? (
        <div className="rounded-2xl bg-felt-900 border border-felt-800 p-8 text-center">
          <p className="text-sm text-felt-100/40">No finished games yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {history.map((g) => {
            const winners = g.players.filter((p) => g.winnerIds?.includes(p.id))
            return (
              <div key={g.id} className="rounded-2xl bg-felt-900 border border-felt-800 p-5">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs text-felt-100/40">
                    {new Date(g.finishedAt ?? g.createdAt).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })}
                  </p>
                  <span className="text-xs text-felt-100/40">{g.rounds.length} rounds</span>
                </div>
                <p className="inline-flex items-center gap-1.5 text-sm font-semibold text-gold-300 mb-3">
                  <Trophy size={14} /> {winners.map((w) => w.name).join(' & ')}
                </p>
                <div className="flex flex-wrap gap-x-4 gap-y-1">
                  {[...g.players]
                    .sort((a, b) => {
                      const totalA = g.rounds.reduce((s, r) => s + (r.finalScores[a.id] ?? 0), 0)
                      const totalB = g.rounds.reduce((s, r) => s + (r.finalScores[b.id] ?? 0), 0)
                      return totalA - totalB
                    })
                    .map((p) => {
                      const total = g.rounds.reduce((s, r) => s + (r.finalScores[p.id] ?? 0), 0)
                      return (
                        <span key={p.id} className="text-xs text-felt-100/60">
                          {p.name} <span className="font-mono text-felt-50">{total}</span>
                        </span>
                      )
                    })}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
