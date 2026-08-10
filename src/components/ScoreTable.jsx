import { Crown, Spade } from 'lucide-react'

export default function ScoreTable({ players, rounds, totals }) {
  const leaderId = players.reduce(
    (leader, p) => (totals[p.id] < totals[leader.id] ? p : leader),
    players[0]
  )

  return (
    <div className="rounded-2xl bg-felt-900 border border-felt-800 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-felt-800">
              <th className="text-left font-medium text-felt-100/40 px-4 py-3 text-xs uppercase tracking-wider">
                Round
              </th>
              {players.map((p) => (
                <th key={p.id} className="text-center font-medium text-felt-50 px-3 py-3 whitespace-nowrap">
                  {p.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rounds.length === 0 && (
              <tr>
                <td colSpan={players.length + 1} className="px-4 py-6 text-center text-felt-100/40 text-sm">
                  No rounds yet — enter one above.
                </td>
              </tr>
            )}
            {rounds.map((round, i) => (
              <tr key={i} className="border-b border-felt-800/60">
                <td className="px-4 py-2.5 text-felt-100/40 text-xs">{i + 1}</td>
                {players.map((p) => {
                  const isCaller = round.caboCallerId === p.id
                  const success = isCaller && round.finalScores[p.id] === 0
                  return (
                    <td key={p.id} className="px-3 py-2.5 text-center font-mono">
                      <span
                        className={
                          isCaller
                            ? success
                              ? 'text-gold-400 font-semibold'
                              : 'text-red-400'
                            : 'text-felt-50'
                        }
                      >
                        {round.finalScores[p.id]}
                      </span>
                      {isCaller && <Spade size={9} className="inline-block ml-1 mb-0.5 text-gold-400" />}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-felt-100/50">
                Total
              </td>
              {players.map((p) => (
                <td key={p.id} className="px-3 py-3 text-center font-mono font-bold">
                  <span
                    className={`inline-flex items-center gap-1 ${
                      p.id === leaderId.id ? 'text-gold-300' : 'text-felt-50'
                    }`}
                  >
                    {p.id === leaderId.id && <Crown size={13} />}
                    {totals[p.id]}
                  </span>
                </td>
              ))}
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}
