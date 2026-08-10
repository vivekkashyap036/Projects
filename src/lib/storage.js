const CURRENT_GAME_KEY = 'cabo:current-game'
const HISTORY_KEY = 'cabo:history'

export function loadCurrentGame() {
  try {
    const raw = localStorage.getItem(CURRENT_GAME_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function saveCurrentGame(game) {
  localStorage.setItem(CURRENT_GAME_KEY, JSON.stringify(game))
}

export function clearCurrentGame() {
  localStorage.removeItem(CURRENT_GAME_KEY)
}

export function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

// Idempotent by game id: safe to call from multiple mounted components
// (e.g. after navigating between routes) without creating duplicate entries.
export function addToHistory(game) {
  const history = loadHistory()
  if (history.some((g) => g.id === game.id)) return
  history.unshift(game)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 50)))
}
