import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useGameStore = defineStore('game', () => {
  const gameId = ref(null)
  const board = ref({})
  const currentTurn = ref('')
  const phase = ref('')
  const dice = ref([0, 0])
  const winner = ref(null)
  const players = ref([])
  const myColor = ref('')
  const recommendation = ref(null)
  const clockOffset = ref(0)

  const isMyTurn = computed(() => currentTurn.value === myColor.value)

  function updateFromState(state) {
    gameId.value = state.game_id
    board.value = state.board
    currentTurn.value = state.current_turn
    phase.value = state.phase
    dice.value = state.dice
    winner.value = state.winner
  }

  function setPlayers(p) { players.value = p }
  function setMyColor(color) { myColor.value = color }
  function setRecommendation(rec) { recommendation.value = rec }
  function setClockOffset(offset) { clockOffset.value = offset }

  function reset() {
    gameId.value = null
    board.value = {}
    currentTurn.value = ''
    phase.value = ''
    dice.value = [0, 0]
    winner.value = null
    players.value = []
    myColor.value = ''
    recommendation.value = null
    clockOffset.value = 0
  }

  return {
    gameId, board, currentTurn, phase, dice, winner,
    players, myColor, recommendation, clockOffset,
    isMyTurn, updateFromState, setPlayers, setMyColor,
    setRecommendation, setClockOffset, reset,
  }
})
