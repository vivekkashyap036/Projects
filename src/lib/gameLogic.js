// Core Cabo scoring rules. See src/lib/rulesContent.js for the full written ruleset.

export const DEFAULT_TARGET_SCORE = 100
export const DEFAULT_CABO_PENALTY = 5

// Given the raw hand totals everyone revealed this round, and who (if anyone)
// called Cabo, work out each player's final round score.
export function computeRoundScores(rawScores, caboCallerId, penalty = DEFAULT_CABO_PENALTY) {
  const entries = Object.entries(rawScores)
  const minRaw = Math.min(...entries.map(([, score]) => score))
  const callerRaw = caboCallerId != null ? rawScores[caboCallerId] : null
  const callerIsStrictLowest =
    caboCallerId != null &&
    callerRaw === minRaw &&
    entries.filter(([, score]) => score === minRaw).length === 1

  const finalScores = {}
  for (const [playerId, raw] of entries) {
    if (playerId === caboCallerId) {
      finalScores[playerId] = callerIsStrictLowest ? 0 : raw + penalty
    } else {
      finalScores[playerId] = raw
    }
  }
  return { finalScores, callerIsStrictLowest }
}

export function totalsAfterRounds(players, rounds) {
  const totals = {}
  for (const player of players) totals[player.id] = 0
  for (const round of rounds) {
    for (const player of players) {
      totals[player.id] += round.finalScores[player.id] ?? 0
    }
  }
  return totals
}

export function isGameOver(totals, targetScore) {
  return Object.values(totals).some((score) => score >= targetScore)
}

export function getWinners(players, totals) {
  const min = Math.min(...players.map((p) => totals[p.id]))
  return players.filter((p) => totals[p.id] === min)
}

export function newPlayerId() {
  return `p_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

export function newGameId() {
  return `g_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}
