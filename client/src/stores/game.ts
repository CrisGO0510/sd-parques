import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { Color, GamePhase, GameStateDto, MoveDto } from 'src/types/domain';

export const useGameStore = defineStore('game', () => {
  const state = ref<GameStateDto | null>(null);
  const availableMoves = ref<MoveDto[]>([]);
  const myColor = ref<Color | null>(null);
  const winnerUsername = ref<string | null>(null);

  const currentTurnColor = computed<Color | null>(() => {
    const st = state.value;
    if (!st || st.turn_order.length === 0) return null;
    const playerIdx = st.turn_order[st.current_turn_index];
    return playerIdx !== undefined ? (st.players[playerIdx]?.color ?? null) : null;
  });

  const isMyTurn = computed<boolean>(() =>
    myColor.value !== null && currentTurnColor.value === myColor.value
  );

  const phase = computed<GamePhase | null>(() => state.value?.phase ?? null);

  const dice = computed<[number, number] | null>(() => {
    const pd = state.value?.pending_dice;
    if (!pd || pd.length !== 2) return null;
    return [pd[0]!, pd[1]!];
  });

  function updateFromStateUpdate(newState: GameStateDto): void {
    state.value = newState;
  }

  function setAvailableMoves(moves: MoveDto[]): void {
    availableMoves.value = moves;
  }

  function setWinner(u: string | null): void {
    winnerUsername.value = u;
  }

  function reset(): void {
    state.value = null;
    availableMoves.value = [];
    myColor.value = null;
    winnerUsername.value = null;
  }

  return {
    state,
    availableMoves,
    myColor,
    winnerUsername,
    currentTurnColor,
    isMyTurn,
    phase,
    dice,
    updateFromStateUpdate,
    setAvailableMoves,
    setWinner,
    reset,
  };
});
