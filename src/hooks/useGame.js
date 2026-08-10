import { useCallback, useEffect, useRef, useState } from 'react'
import {
  addToHistory,
  clearCurrentGame,
  loadCurrentGame,
  saveCurrentGame,
} from '../lib/storage'
import {
  computeRoundScores,
  getWinners,
  isGameOver,
  newGameId,
  totalsAfterRounds,
} from '../lib/gameLogic'

export function useGame() {
  const [game, setGame] = useState(() => loadCurrentGame())
  const recordedGameIds = useRef(new Set())

  useEffect(() => {
    if (game) saveCurrentGame(game)
  }, [game])

  // Record a finished game to history exactly once, outside of the setState
  // updater (which React/StrictMode may invoke more than once).
  useEffect(() => {
    if (game?.status === 'finished' && !recordedGameIds.current.has(game.id)) {
      recordedGameIds.current.add(game.id)
      addToHistory(game)
    }
  }, [game])

  const startGame = useCallback((players, targetScore, penalty) => {
    const newGame = {
      id: newGameId(),
      createdAt: Date.now(),
      players,
      targetScore,
      penalty,
      rounds: [],
      status: 'active',
    }
    setGame(newGame)
    return newGame
  }, [])

  const addRound = useCallback((rawScores, caboCallerId) => {
    setGame((prev) => {
      if (!prev) return prev
      const { finalScores } = computeRoundScores(rawScores, caboCallerId, prev.penalty)
      const rounds = [...prev.rounds, { rawScores, caboCallerId, finalScores }]
      const totals = totalsAfterRounds(prev.players, rounds)
      const finished = isGameOver(totals, prev.targetScore)
      return {
        ...prev,
        rounds,
        status: finished ? 'finished' : 'active',
        winnerIds: finished ? getWinners(prev.players, totals).map((p) => p.id) : undefined,
        finishedAt: finished ? Date.now() : undefined,
      }
    })
  }, [])

  const undoLastRound = useCallback(() => {
    setGame((prev) => {
      if (!prev || prev.rounds.length === 0) return prev
      return { ...prev, rounds: prev.rounds.slice(0, -1), status: 'active', winnerIds: undefined }
    })
  }, [])

  const endGame = useCallback(() => {
    clearCurrentGame()
    setGame(null)
  }, [])

  const totals = game ? totalsAfterRounds(game.players, game.rounds) : {}

  return { game, totals, startGame, addRound, undoLastRound, endGame }
}
