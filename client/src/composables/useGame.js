import { useSocket } from './useSocket'
import { useGameStore } from 'src/stores/gameStore'

export function useGame() {
  const { getSocket } = useSocket()
  const gameStore = useGameStore()

  function rollDice() { getSocket()?.emit('roll_dice') }
  function movePiece(pieceIndex) { getSocket()?.emit('move_piece', { piece_index: pieceIndex }) }
  function passTurn() { getSocket()?.emit('pass_turn') }
  function requestRecommendation() { getSocket()?.emit('request_recommendation') }
  function finishPieceChoice(pieceIndex) { getSocket()?.emit('finish_piece_choice', { piece_index: pieceIndex }) }

  function setupListeners() {
    const socket = getSocket()
    if (!socket) return
    socket.on('board_update', (state) => { gameStore.updateFromState(state) })
    socket.on('dice_result', (data) => { gameStore.dice = [data.dice_1, data.dice_2] })
    socket.on('recommendation', (data) => { gameStore.setRecommendation(data) })
    socket.on('game_over', (data) => { gameStore.winner = data.winner })
    socket.on('sync_request', () => {
      socket.emit('sync_response', { game_room: `game_${gameStore.gameId}`, client_time: Date.now() })
    })
    socket.on('sync_adjust', (data) => { gameStore.setClockOffset(data.offset_ms) })
  }

  return { rollDice, movePiece, passTurn, requestRecommendation, finishPieceChoice, setupListeners }
}
